from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.http import HttpResponse
from ninja import File, Form, Router, Status, UploadedFile
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Claim, ClaimStatusHistory, Document, Product
from assurex_claim_engine.decision.fusion import generate_narrative_summary
from assurex_claim_engine.reporting.pdf_generator import generate_claim_pdf_report
from assurex_claim_engine.web.helpers import (
    apply_claim_filters,
    paginate,
    scoped_claims,
    write_audit,
)

from ..deps import auth, current_principal, db_of, require_roles
from ..schemas import PrecheckIn
from ..serializers import claim_dossier, claim_out, document_out, pagination_out, status_history_out
from ..services import claim_flow

router = Router(tags=["Claims"], auth=auth)


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
@router.get("/claims")
def list_claims(
    request,
    claim_id: str = "",
    product_id: str = "",
    serial: str = "",
    category: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    per_page: int = 15,
):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    query = apply_claim_filters(
        scoped_claims(db, user),
        {
            "claim_id": claim_id,
            "product_id": product_id,
            "serial": serial,
            "category": category,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    pagination = paginate(query.order_by(Claim.created_at.desc()), page=page, per_page=per_page)
    items = []
    for claim in pagination["items"]:
        product = db.query(Product).filter(Product.product_id == claim.product_id).first()
        items.append(claim_out(claim, product))
    return pagination_out(pagination, items)


# --------------------------------------------------------------------------- #
# Static sub-routes (must be declared before /claims/{claim_id})
# --------------------------------------------------------------------------- #
@router.post("/claims/precheck")
def precheck(request, payload: PrecheckIn):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    return claim_flow.precheck(db, user, payload.model_dump())


@router.post("/claims", response={201: dict})
def submit_claim(
    request,
    product_id: str = Form(""),
    product_name: str = Form(""),
    product_category: str = Form("electronics"),
    brand: str = Form(""),
    model_number: str = Form(""),
    serial_number: str = Form(""),
    purchase_date: str = Form(""),
    purchase_price: float = Form(0),
    retailer: str = Form(""),
    warranty_months: int = Form(24),
    has_extended_warranty: bool = Form(False),
    extended_warranty_provider: str = Form(""),
    extended_warranty_contract_number: str = Form(""),
    extended_warranty_duration_months: int = Form(0),
    fault_category: str = Form("motherboard_failure"),
    damage_type: str = Form("none"),
    fault_occurrence_date: str = Form(""),
    claim_submission_date: str = Form(""),
    description: str = Form(""),
    previous_repairs_count: Optional[int] = Form(None),
    has_unauthorized_repairs: bool = Form(False),
    receipt_file: Optional[UploadedFile] = File(None),
    warranty_card_file: Optional[UploadedFile] = File(None),
    product_photo_file: Optional[UploadedFile] = File(None),
    serial_photo_file: Optional[UploadedFile] = File(None),
    damage_photo_file: Optional[UploadedFile] = File(None),
    attach_doc_ids: str = Form(""),
    action_type: str = Form("submit"),
    draft_id: Optional[str] = Form(None),
):
    """Create a claim.

    ``action_type=draft`` stores a draft without running the ML pipeline.
    Any other value performs full dual-model adjudication and returns the
    resulting claim, including the dossier.
    """
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    payload = {
        "product_id": product_id,
        "product_name": product_name,
        "product_category": product_category,
        "brand": brand,
        "model_number": model_number,
        "serial_number": serial_number,
        "purchase_date": purchase_date,
        "purchase_price": purchase_price,
        "retailer": retailer,
        "warranty_months": warranty_months,
        "has_extended_warranty": has_extended_warranty,
        "extended_warranty_provider": extended_warranty_provider,
        "extended_warranty_contract_number": extended_warranty_contract_number,
        "extended_warranty_duration_months": extended_warranty_duration_months,
        "fault_category": fault_category,
        "damage_type": damage_type,
        "fault_occurrence_date": fault_occurrence_date,
        "claim_submission_date": claim_submission_date,
        "description": description,
        "previous_repairs_count": previous_repairs_count,
        "has_unauthorized_repairs": has_unauthorized_repairs,
        "attach_doc_ids": attach_doc_ids,
        "action_type": action_type,
        "draft_id": draft_id,
    }
    files = {
        "receipt_file": receipt_file,
        "warranty_card_file": warranty_card_file,
        "product_photo_file": product_photo_file,
        "serial_photo_file": serial_photo_file,
        "damage_photo_file": damage_photo_file,
    }

    claim = claim_flow.submit_claim(db, user, payload, files)
    product = db.query(Product).filter(Product.product_id == claim.product_id).first()

    body = claim_out(claim, product)
    body["dossier"] = claim_dossier(claim)
    return Status(201, body)


@router.post("/claims/import-csv")
def import_csv(request, upload: UploadedFile = File(...)):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)

    if not (upload.name or "").lower().endswith(".csv"):
        raise HttpError(400, "Uploaded file must be a .csv file.")
    return claim_flow.import_claims_csv(db, user, upload.read())


# --------------------------------------------------------------------------- #
# Item routes
# --------------------------------------------------------------------------- #
@router.get("/claims/{claim_id}")
def get_claim(request, claim_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)

    _require_claim_access(user, claim)

    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = claim_dossier(claim)
    narrative = dossier.get("narrative_summary") or generate_narrative_summary(
        claim, product=product, dossier=dossier
    )
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()

    payload = claim_out(claim, product)
    payload.update(
        {
            "dossier": dossier,
            "narrative_summary": narrative,
            "documents": [document_out(d) for d in documents],
        }
    )
    return payload


@router.get("/claims/{claim_id}/history")
def claim_history(request, claim_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)
    _require_claim_access(user, claim)

    rows = (
        db.query(ClaimStatusHistory)
        .filter(ClaimStatusHistory.claim_id == claim_id)
        .order_by(ClaimStatusHistory.created_at.asc(), ClaimStatusHistory.id.asc())
        .all()
    )
    return {"claim_id": claim_id, "history": [status_history_out(row) for row in rows]}


@router.get("/claims/{claim_id}/dossier")
def get_claim_dossier(request, claim_id: str):
    return get_claim(request, claim_id)


@router.get("/claims/{claim_id}/summary-card")
def get_summary_card(request, claim_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)
    _require_claim_access(user, claim)

    path = settings.UPLOADS_DIR / f"{claim_id}_summary_card.png"
    if not path.is_file():
        raise HttpError(404, "Summary card not found for this claim.")
    response = HttpResponse(path.read_bytes(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="{claim_id}_summary_card.png"'
    return response


@router.post("/claims/{claim_id}/documents/{doc_id}")
def attach_document(request, claim_id: str, doc_id: str):
    principal = require_roles("customer", "service_center")(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)
    _require_claim_access(user, claim)

    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if document is None:
        raise HttpError(404, "Document not found.")
    if user.role not in ("admin", "reviewer") and document.user_id not in (None, user.user_id):
        raise HttpError(403, "You cannot attach this document.")

    document.claim_id = claim.claim_id
    document.product_id = claim.product_id
    write_audit(
        db,
        action="Document Attached",
        performed_by=user.user_id,
        user_id=user.user_id,
        claim_id=claim_id,
        entity_type="document",
        entity_id=doc_id,
        details={"via": "rest_api"},
    )
    db.commit()
    return {"detail": f"Document {doc_id} attached to claim {claim_id}."}


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
@router.get("/claims/{claim_id}/report.pdf")
def claim_report_pdf(request, claim_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)
    _require_claim_access(user, claim)

    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = claim_dossier(claim)
    narrative = dossier.get("narrative_summary") or generate_narrative_summary(
        claim, product=product, dossier=dossier
    )
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()

    pdf_bytes = generate_claim_pdf_report(
        claim, product, dossier, narrative_summary=narrative, documents=documents
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{claim_id}_adjudication_report.pdf"'
    )
    return response


@router.get("/claims/{claim_id}/report.md")
def claim_report_markdown(request, claim_id: str):
    principal = current_principal(request)
    db = db_of(request)
    user = _user(db, principal.user_id)
    claim = _claim(db, claim_id)
    _require_claim_access(user, claim)

    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = claim_dossier(claim)
    narrative = dossier.get("narrative_summary") or generate_narrative_summary(
        claim, product=product, dossier=dossier
    )
    explanation = dossier.get("explanation") or {}
    lines = [
        f"# AssureX Claim Report — {claim.claim_id}",
        "",
        "## Executive Summary",
        narrative,
        "",
        f"- Product: {product.product_name if product else claim.product_id}",
        f"- Status: {claim.status}",
        f"- Final decision: {claim.final_decision}",
        f"- Model version: {claim.model_version or 'n/a'}",
        f"- Python: {claim.python_predicted_class} ({claim.python_top_confidence})",
        f"- Vision: {claim.vision_predicted_class} ({claim.vision_top_confidence})",
        f"- Consistency: {claim.consistency_status}",
        "",
        "## Supporting factors",
        *[f"- {x}" for x in (explanation.get("supporting_factors") or ["None"])],
        "",
        "## Opposing factors",
        *[f"- {x}" for x in (explanation.get("opposing_factors") or ["None"])],
        "",
        "## Reviewer comments",
        claim.reviewer_comments or "None",
    ]
    body = "\n".join(lines)
    response = HttpResponse(body, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{claim_id}_report.md"'
    return response


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _require_claim_access(user, claim: Claim) -> None:
    if user.role in ("admin", "reviewer"):
        return
    if claim.user_id != user.user_id:
        raise HttpError(403, "You cannot access this claim.")


def _claim(db, claim_id: str) -> Claim:
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if claim is None:
        raise HttpError(404, "Claim not found.")
    return claim


def _user(db, user_id: str):
    from assurex_claim_engine.db.database import User

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:  # pragma: no cover
        raise HttpError(401, "User no longer exists.")
    return user
