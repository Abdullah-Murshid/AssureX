"""
Tests for PDF OCR extraction via PyMuPDF in DocumentOCRParser.
"""

import os
import pymupdf
import pytest
from assurex_claim_engine.ocr.parser import DocumentOCRParser


def test_pdf_ocr_extraction_from_bytes():
    """Generates an in-memory PDF receipt and verifies field extraction."""
    doc = pymupdf.open()
    page = doc.new_page()
    text = (
        "OFFICIAL RECEIPT / INVOICE\n"
        "Invoice Number: INV-771234\n"
        "Date of Purchase: 2025-04-12\n"
        "Retailer: Tech World MegaStore\n"
        "Item: UltraBook Pro 15\n"
        "Model: MOD-9921X\n"
        "Warranty Duration: 24 Months\n"
        "Serial Number: SN9876543210\n"
        "Total Paid: 899.50\n"
    )
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = DocumentOCRParser()
    result = parser.extract_receipt_data(pdf_bytes)

    assert result["extracted_invoice_number"] == "INV-771234"
    assert result["extracted_purchase_date"] == "2025-04-12"
    assert result["extracted_retailer"] == "Tech World MegaStore"
    assert result["extracted_model_number"] == "MOD-9921X"
    assert result["extracted_product_name"] == "UltraBook Pro 15"
    assert "24 Months" in (result["extracted_warranty_period"] or "")
    assert result["extracted_serial_number"] == "SN9876543210" or result["extracted_serial_number"] == "9876543210"
    assert result["extracted_amount"] == 899.50
    assert result["extraction_confidence"] == 0.95


def test_pdf_ocr_extraction_from_file(tmp_path):
    """Generates a temporary PDF file and tests path-based extraction."""
    doc = pymupdf.open()
    page = doc.new_page()
    text = (
        "TAX INVOICE BILL-992144\n"
        "Purchase Date: 2025-11-20\n"
        "Serial: SN1234567890\n"
        "Amount: 249.99\n"
    )
    page.insert_text((50, 72), text)
    pdf_file = tmp_path / "test_invoice.pdf"
    doc.save(str(pdf_file))
    doc.close()

    parser = DocumentOCRParser()
    result = parser.extract_receipt_data(str(pdf_file))

    assert result["extracted_invoice_number"] == "BILL-992144"
    assert result["extracted_purchase_date"] == "2025-11-20"
    assert result["extracted_amount"] == 249.99
    assert result["extraction_confidence"] == 0.95
