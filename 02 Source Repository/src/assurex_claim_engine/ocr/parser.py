"""
AssureX Claim Engine - Document OCR & SHA-256 Hashing Engine
Provides file security hashing and receipt OCR data extraction:
- Computes SHA-256 document hash to detect duplicate uploaded files
- Extracts Purchase Date, Invoice Number, Model/Serial Number, Retailer, and Total Amount
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import re
import hashlib
from typing import Dict, Any

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz as pymupdf
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False

try:
    from config.settings_loader import get
except ImportError:
    def get(k, d=None):
        return {"pdf_render_dpi": 200}.get(k, d)

class DocumentOCRParser:
    def __init__(self):
        self.reader = None
        self._init_attempted = False

    def get_reader(self):
        """Lazy load EasyOCR reader on-demand only when extracting text."""
        if self.reader is None and not self._init_attempted:
            self._init_attempted = True
            try:
                import easyocr
                self.reader = easyocr.Reader(['en'], gpu=False)
            except Exception as e:
                print(f"EasyOCR init warning: {e}")
                self.reader = None
        return self.reader

    @staticmethod
    def compute_file_hash(file_bytes_or_path) -> str:
        """
        Computes SHA-256 hash of a file or byte buffer.
        """
        hasher = hashlib.sha256()
        if isinstance(file_bytes_or_path, str):
            with open(file_bytes_or_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        elif isinstance(file_bytes_or_path, bytes):
            hasher.update(file_bytes_or_path)
        else:
            # Assume file object
            file_bytes_or_path.seek(0)
            hasher.update(file_bytes_or_path.read())
            file_bytes_or_path.seek(0)
        return hasher.hexdigest()

    def _extract_from_pdf(self, pdf_path_or_bytes) -> str:
        """Extract text from PDF: embedded text first; fallback to rendering pages at 200 dpi."""
        if not PYMUPDF_AVAILABLE:
            return ""

        try:
            if isinstance(pdf_path_or_bytes, bytes):
                doc = pymupdf.open(stream=pdf_path_or_bytes, filetype="pdf")
            else:
                doc = pymupdf.open(pdf_path_or_bytes)
        except Exception as e:
            print(f"PyMuPDF open error: {e}")
            return ""

        extracted_text = ""
        # 1. Try embedded text
        for page in doc:
            page_text = page.get_text()
            if page_text:
                extracted_text += page_text + " "

        # 2. If embedded text is present, return it directly
        if len(extracted_text.strip()) > 10:
            doc.close()
            return extracted_text.strip()

        # 3. Else fallback to rendering at 200 dpi and applying EasyOCR
        reader = self.get_reader()
        if not reader:
            doc.close()
            return extracted_text.strip()

        dpi = get("pdf_render_dpi", 200)
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)

        rendered_text_parts = []
        for page in doc:
            try:
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                results = reader.readtext(img_bytes, detail=0)
                rendered_text_parts.extend(results)
            except Exception as e:
                print(f"Error OCR rendering PDF page: {e}")

        doc.close()
        return " ".join(rendered_text_parts).strip()

    def extract_receipt_data(self, image_path_or_bytes) -> Dict[str, Any]:
        """
        Extracts structured fields from uploaded receipt / invoice document image or PDF.
        """
        extracted_text = ""
        is_pdf = False

        if isinstance(image_path_or_bytes, str) and image_path_or_bytes.lower().endswith(".pdf"):
            is_pdf = True
        elif isinstance(image_path_or_bytes, bytes) and image_path_or_bytes.startswith(b"%PDF"):
            is_pdf = True

        if is_pdf:
            extracted_text = self._extract_from_pdf(image_path_or_bytes)
        else:
            try:
                import concurrent.futures
                from PIL import Image

                def _run_image_ocr():
                    reader = self.get_reader()
                    if not reader or not isinstance(image_path_or_bytes, str) or not os.path.exists(image_path_or_bytes):
                        return ""
                    tmp_name = None
                    try:
                        with Image.open(image_path_or_bytes) as img:
                            img = img.convert("RGB")
                            img.thumbnail((640, 640))
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                                tmp_name = tmp.name
                            img.save(tmp_name, "JPEG", quality=80)
                        results = reader.readtext(tmp_name, detail=0)
                        return " ".join(results)
                    except Exception:
                        results = reader.readtext(image_path_or_bytes, detail=0)
                        return " ".join(results)
                    finally:
                        if tmp_name and os.path.exists(tmp_name):
                            try:
                                os.remove(tmp_name)
                            except Exception:
                                pass

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_image_ocr)
                    extracted_text = future.result(timeout=3.5)
            except Exception as e:
                print(f"OCR execution warning / timeout: {e}")
                extracted_text = ""

        # Regex Pattern Extractions
        date_match = re.search(r'\b(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})\b', extracted_text)
        invoice_match = re.search(r'\b(INV[-#]?\d{4,8}|BILL[-#]?\d{4,8}|\d{6,10})\b', extracted_text, re.IGNORECASE)
        amount_match = re.search(r'\$?\b(\d{2,5}\.\d{2})\b', extracted_text)
        serial_match = re.search(r'(?:SN|S/N|Serial(?: Number)?|SERIAL)[:#]?\s*([A-Z0-9]{6,16})\b', extracted_text, re.IGNORECASE)
        if not serial_match:
            serial_match = re.search(r'\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{8,14}\b', extracted_text)

        # Extended Module VI Extractions: Retailer, Model Number, Product Name, Warranty Duration
        retailer_match = re.search(
            r'(?:Retailer|Store|Merchant|Vendor|Seller|Sold By)[:#]?\s*([A-Za-z0-9 &.,\'-]{2,40})',
            extracted_text,
            re.IGNORECASE
        )
        if not retailer_match:
            retailer_match = re.search(
                r'\b(Best Buy|Amazon(?:\.com)?|Walmart|Target|Micro Center|Costco|B&H Photo|Apple Store|Home Depot|Currys|Newegg|Samsung Store|Sony Store|Reliance Digital|Croma|Carrefour)\b',
                extracted_text,
                re.IGNORECASE
            )

        model_match = re.search(
            r'(?:Model(?: Number| No| #)?|Item (?:No|#)|MOD|MN)[:#]?\s*([A-Z0-9][-A-Z0-9/]{2,20})\b',
            extracted_text,
            re.IGNORECASE
        )
        if not model_match:
            model_match = re.search(r'\b(MOD[-_][A-Z0-9]{3,10}|[A-Z]{2,4}[-_]?\d{3,5}[A-Z0-9]*)\b', extracted_text)

        product_match = re.search(
            r'(?:Product(?: Name)?|Item(?: Description| Name)?|Description|Desc)[:#]?\s*([A-Za-z0-9 &.,\'/+\-]{3,45})',
            extracted_text,
            re.IGNORECASE
        )

        warranty_match = re.search(
            r'(?:Warranty(?: Period| Duration)?|Coverage)[:#]?\s*(\d{1,2}\s*(?:Months?|Mos?|Years?|Yrs?))\b',
            extracted_text,
            re.IGNORECASE
        )

        purchase_date = date_match.group(1) if date_match else None
        invoice_number = invoice_match.group(1) if invoice_match else None
        amount = float(amount_match.group(1)) if amount_match else None
        extracted_serial = serial_match.group(1) if serial_match else None

        retailer_name = retailer_match.group(1).strip() if retailer_match else None
        if retailer_name:
            retailer_name = re.split(r'[\r\n]', retailer_name)[0].strip()

        model_number = model_match.group(1).strip() if model_match else None
        product_name = product_match.group(1).strip() if product_match else None
        if product_name:
            product_name = re.split(r'[\r\n]', product_name)[0].strip()

        warranty_period = warranty_match.group(1).strip() if warranty_match else None

        return {
            "raw_text": extracted_text,
            "extracted_purchase_date": purchase_date,
            "extracted_invoice_number": invoice_number,
            "extracted_amount": amount,
            "extracted_serial_number": extracted_serial,
            "extracted_retailer": retailer_name,
            "extracted_model_number": model_number,
            "extracted_product_name": product_name,
            "extracted_warranty_period": warranty_period,
            "extraction_confidence": 0.95 if (is_pdf and extracted_text) else (0.88 if extracted_text else 0.0)
        }

if __name__ == "__main__":
    ocr_parser = DocumentOCRParser()
    test_hash = ocr_parser.compute_file_hash(b"AssureX Sample File Content")
    print("Test SHA-256 Hash:", test_hash)
