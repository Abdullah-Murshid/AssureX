from __future__ import annotations

import json
import mimetypes
import os
from datetime import datetime, timezone

from django.http import HttpResponse
from ninja import File, Form, Router, Status, UploadedFile
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Document, Product
from assurex_claim_engine.web.helpers import (
    find_hash_duplicates,
    next_doc_id,
    paginate,
    scoped_documents,
    scoped_products,
    validate_upload,
    write_audit,
)

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import DocumentVerifyIn
from ..serializers import document_out, pagination_out
from ..services.models import registry
from ..services.storage import resolve_stored_path, save_upload

router = Router(tags=["Documents"], auth=auth)


def _ocr():
    return registry.ocr_parser()


@router.get("/documents")
def list_documents(
    request,
    file_type: str = "",
    product_id: str = "",
    claim_id: str = "",
    page: int = 1,
    per_page: int = 15,
):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    query = scoped_documents(db, user)
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if product_id:
        query = query.filter(Document.product_id == product_id)
    if claim_id:
        query = query.filter(Document.claim_id == claim_id)

    pagination = paginate(query.order_by(Document.created_at.desc()), page=page, per_page=per_page)
    items = [
        document_out(doc, find_hash_duplicates(db, doc.file_hash, exclude_doc_id=doc.doc_id))
        for doc in pagination["items"]
    ]
    return pagination_out(pagination, items)


@router.post("/documents", response={201: dict})
def upload_document(
    request,
    upload: UploadedFile = File(...),
    file_type: str = Form("purchase_receipt"),
    product_id: str = Form(""),
):
    """Upload a standalone evidence file into the document vault."""
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    contents = upload.read()
    error = validate_upload(upload.name, len(contents), receipt_only=True)
    if error:
        raise HttpError(400, error)

    product = None
    if product_id:
        product = scoped_products(db, user).filter(Product.product_id == product_id).first()
        if product is None:
            raise HttpError(404, "Product not found.")

    doc_id = next_doc_id(db)
    rel_path, absolute = save_upload(contents, f"{doc_id}_{os.path.basename(upload.name)}")

    extracted: dict = {}
    if file_type in ("purchase_receipt", "receipt", "warranty_card"):
        try:
            extracted = _ocr().extract_receipt_data(str(absolute))
        except Exception:  # pragma: no cover - OCR is best effort
            extracted = {}

    file_hash = _ocr().compute_file_hash(contents)
    duplicates = find_hash_duplicates(db, file_hash)

    document = Document(
        doc_id=doc_id,
        claim_id=None,
        product_id=product.product_id if product else None,
        user_id=user.user_id,
        file_name=os.path.basename(upload.name),
        file_type=file_type,
        file_path=rel_path,
        file_hash=file_hash,
        extracted_data_json=json.dumps(extracted) if extracted else None,
    )
    db.add(document)
    write_audit(
        db,
        action="Document Upload",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={"hash": file_hash, "duplicates": [d.doc_id for d in duplicates], "via": "rest_api"},
    )
    db.commit()
    db.refresh(document)

    payload = document_out(document, duplicates)
    payload["warning"] = (
        f"Duplicate document hash matches {len(duplicates)} existing file(s)."
        if duplicates
        else None
    )
    return Status(201, payload)


@router.get("/documents/{doc_id}")
def get_document(request, doc_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    document = scoped_documents(db, user).filter(Document.doc_id == doc_id).first()
    if document is None:
        raise HttpError(404, "Document not found.")
    return document_out(
        document,
        find_hash_duplicates(db, document.file_hash, exclude_doc_id=document.doc_id),
    )


@router.get("/documents/{doc_id}/download")
def download_document(request, doc_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    document = scoped_documents(db, user).filter(Document.doc_id == doc_id).first()
    if document is None:
        raise HttpError(404, "Document not found.")

    path = resolve_stored_path(document.file_path)
    if not path.is_file():
        raise HttpError(404, "Stored file is missing.")

    content_type = mimetypes.guess_type(document.file_name)[0] or "application/octet-stream"
    response = HttpResponse(path.read_bytes(), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{document.file_name}"'
    return response


@router.get("/documents/{doc_id}/file")
def download_document_alias(request, doc_id: str):
    return download_document(request, doc_id)


@router.post("/documents/{doc_id}/verify")
def verify_document(request, doc_id: str, payload: DocumentVerifyIn):
    """Save human-corrected OCR fields for a document."""
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    document = _owned_document(db, user, doc_id)

    original = {}
    if document.extracted_data_json:
        try:
            original = json.loads(document.extracted_data_json)
        except (ValueError, TypeError):
            original = {}

    updated = {
        "extracted_purchase_date": payload.purchase_date,
        "extracted_invoice_number": payload.invoice_number,
        "extracted_product_name": payload.product_name,
        "extracted_model_number": payload.model_number,
        "extracted_serial_number": payload.serial_number,
        "extracted_retailer": payload.retailer_name,
        "extracted_amount": payload.purchase_amount,
        "extracted_warranty_period": payload.warranty_period,
    }
    document.extracted_data_json = json.dumps(updated)
    document.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    document.verified_by = user.user_id
    write_audit(
        db,
        action="OCR Correction",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={"before": original, "after": updated, "via": "rest_api"},
    )
    db.commit()
    db.refresh(document)
    return document_out(document)


@router.post("/documents/{doc_id}/replace")
def replace_document(
    request,
    doc_id: str,
    upload: UploadedFile = File(...),
    file_type: str = Form(""),
):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    document = _owned_document(db, user, doc_id)

    contents = upload.read()
    error = validate_upload(upload.name, len(contents), receipt_only=False)
    if error:
        raise HttpError(400, error)

    old_path = resolve_stored_path(document.file_path)
    if old_path.is_file():
        try:
            old_path.unlink()
        except OSError:  # pragma: no cover - best effort
            pass

    rel_path, absolute = save_upload(contents, f"{doc_id}_{os.path.basename(upload.name)}")
    new_hash = _ocr().compute_file_hash(contents)
    effective_type = file_type or document.file_type or "purchase_receipt"

    extracted: dict = {}
    if effective_type in ("purchase_receipt", "receipt", "warranty_card"):
        try:
            extracted = _ocr().extract_receipt_data(str(absolute))
        except Exception:  # pragma: no cover
            extracted = {}

    old_hash = document.file_hash
    document.file_name = os.path.basename(upload.name)
    document.file_path = rel_path
    document.file_hash = new_hash
    document.file_type = effective_type
    document.extracted_data_json = json.dumps(extracted) if extracted else None
    document.verified_at = None
    document.verified_by = None

    duplicates = find_hash_duplicates(db, new_hash, exclude_doc_id=doc_id)
    write_audit(
        db,
        action="Document Replace",
        performed_by=user.user_id,
        user_id=user.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={
            "old_hash": old_hash,
            "new_hash": new_hash,
            "duplicates": [d.doc_id for d in duplicates],
            "via": "rest_api",
        },
    )
    db.commit()
    db.refresh(document)
    return document_out(document, duplicates)


@router.delete("/documents/{doc_id}")
def delete_document(request, doc_id: str):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    document = _owned_document(db, user, doc_id)

    path = resolve_stored_path(document.file_path)
    if path.is_file():
        try:
            path.unlink()
        except OSError:  # pragma: no cover
            pass

    write_audit(
        db,
        action="Document Delete",
        performed_by=user.user_id,
        user_id=document.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={
            "file_name": document.file_name,
            "file_hash": document.file_hash,
            "claim_id": document.claim_id,
            "product_id": document.product_id,
            "via": "rest_api",
        },
    )
    db.delete(document)
    db.commit()
    return {"detail": f"Document {doc_id} deleted."}


def _owned_document(db, user, doc_id: str) -> Document:
    """Load a document for mutation; reviewer is blocked by require_roles."""
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if document is None:
        raise HttpError(404, "Document not found.")
    if user.role != "admin" and document.user_id != user.user_id:
        raise HttpError(403, "You can only modify documents you own.")
    return document


def _user(db, user_id: str):
    from assurex_claim_engine.db.database import User

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    return user
