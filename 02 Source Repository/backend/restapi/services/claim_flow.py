"""Claim intake and adjudication orchestration.

This module ports the ``POST /claims/submit`` and ``POST /claims/import-csv``
business logic from the legacy FastAPI application into reusable functions that
the Django Ninja routers call. The ML pipeline itself is untouched: the same
tabular model, Teachable Machine model, summary-card renderer, policy rule
engine and fusion engine are used.
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from ninja.errors import HttpError
from sqlalchemy.orm import Session

from assurex_claim_engine.db.database import Claim, Document, Product, User
from assurex_claim_engine.db.status_history import ensure_initial_status, record_status_transition, record_submission_stages
from assurex_claim_engine import notifications as notification_service
from assurex_claim_engine.decision.derived_features import compute_derived_claim_features
from assurex_claim_engine.web.helpers import (
    FILE_TYPE_MAP,
    documents_by_policy_key,
    load_policy,
    next_claim_id,
    next_doc_id,
    next_product_id,
    product_to_claim_dict,
    repair_stats_for_product,
    scoped_claims,
    scoped_documents,
    scoped_products,
    validate_upload,
    write_audit,
)
from config.settings_loader import get
from dataset_generator.generate_summary_cards_v6 import render_claim_card_v6 as render_claim_card

from .models import ModelNotReady, registry
from .storage import save_upload, uploads_dir


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def _ocr():
    return registry.ocr_parser()


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _dedupe_payload(payload: dict) -> dict:
    """Drop ``None`` values so defaults from the product/claim model apply."""
    return {k: v for k, v in (payload or {}).items() if v is not None}


# --------------------------------------------------------------------------- #
# Claim submission
# --------------------------------------------------------------------------- #
def submit_claim(
    db: Session,
    user: User,
    payload: dict,
    files: Optional[dict[str, Any]] = None,
) -> Claim:
    """Create/update a claim (draft or fully evaluated) and return the row."""
    files = files or {}
    payload = _dedupe_payload(payload)
    is_draft = str(payload.get("action_type") or "submit").lower() == "draft"

    if not is_draft:
        try:
            registry.ensure_ready()
        except ModelNotReady as exc:
            raise HttpError(503, str(exc)) from exc

    fault_occurrence_date = (payload.get("fault_occurrence_date") or "").strip()
    if not fault_occurrence_date:
        if is_draft:
            fault_occurrence_date = _today()
        else:
            raise HttpError(400, "Fault occurrence date is required.")

    claim_submission_date = (payload.get("claim_submission_date") or "").strip() or _today()

    try:
        # ------------------------------------------------------------ #
        # 1. Resolve or register the product
        # ------------------------------------------------------------ #
        product: Optional[Product] = None
        product_id = (payload.get("product_id") or "").strip()
        if product_id:
            product = (
                scoped_products(db, user)
                .filter(Product.product_id == product_id)
                .first()
            )
            if product is None:
                raise HttpError(400, "Selected product was not found.")

        if product is None:
            if is_draft and not payload.get("product_name"):
                product = scoped_products(db, user).first()
            if product is None:
                if not (
                    payload.get("product_name")
                    and payload.get("serial_number")
                    and payload.get("purchase_date")
                ):
                    raise HttpError(
                        400,
                        "Register a product first or complete the new-product fields "
                        "(product_name, serial_number, purchase_date).",
                    )
                product = Product(
                    product_id=next_product_id(db),
                    user_id=user.user_id,
                    product_name=payload["product_name"],
                    category=payload.get("product_category") or payload.get("category") or "electronics",
                    brand=payload.get("brand") or "Generic",
                    model_number=payload.get("model_number") or "N/A",
                    serial_number=payload["serial_number"],
                    purchase_date=payload["purchase_date"],
                    purchase_price=float(payload.get("purchase_price") or 0),
                    retailer=payload.get("retailer") or "Unknown",
                    warranty_duration_months=int(payload.get("warranty_months") or 24),
                    has_extended_warranty=bool(
                        payload.get("has_extended_warranty")
                        or payload.get("extended_warranty_provider")
                        or payload.get("extended_warranty_contract_number")
                        or int(payload.get("extended_warranty_duration_months") or 0) > 0
                    ),
                    extended_warranty_provider=(payload.get("extended_warranty_provider") or "").strip(),
                    extended_warranty_contract_number=(payload.get("extended_warranty_contract_number") or "").strip(),
                    extended_warranty_duration_months=int(payload.get("extended_warranty_duration_months") or 0),
                )
                db.add(product)
                db.flush()
                write_audit(
                    db,
                    action="Product Registration",
                    performed_by=user.user_id,
                    user_id=user.user_id,
                    entity_type="product",
                    entity_id=product.product_id,
                    details={"via": "claim_submit"},
                )

        # ------------------------------------------------------------ #
        # 2. Resolve the claim identifier
        # ------------------------------------------------------------ #
        db_claim: Optional[Claim] = None
        draft_id = (payload.get("draft_id") or "").strip()
        if draft_id:
            db_claim = (
                scoped_claims(db, user).filter(Claim.claim_id == draft_id).first()
            )
        claim_id = db_claim.claim_id if db_claim else next_claim_id(db)

        # ------------------------------------------------------------ #
        # 3. Persist uploaded evidence
        # ------------------------------------------------------------ #
        upload_specs = [
            ("receipt_file", "purchase_receipt"),
            ("warranty_card_file", "warranty_card"),
            ("product_photo_file", "product_image"),
            ("serial_photo_file", "serial_number_photo"),
            ("damage_photo_file", "damage_photo"),
        ]
        file_hash = ""
        ocr_extracted: dict = {}
        pending_docs: list[dict] = []

        for field_name, ftype in upload_specs:
            upload = files.get(field_name)
            if not upload:
                continue
            contents = upload.read()
            err = validate_upload(
                getattr(upload, "name", ""),
                len(contents),
                receipt_only=ftype in ("purchase_receipt", "warranty_card"),
            )
            if err:
                raise HttpError(400, err)
            clean_filename = os.path.basename(upload.name)
            save_name = f"{claim_id}_{ftype}_{clean_filename}"
            rel_path, _absolute = save_upload(contents, save_name)

            extracted: dict = {}
            if ftype == "purchase_receipt":
                try:
                    extracted = _ocr().extract_receipt_data(str(_absolute))
                except Exception as exc:  # pragma: no cover - OCR is best effort
                    print(f"[api] OCR extraction failed: {exc}", flush=True)
                    extracted = {}
                ocr_extracted = extracted
                file_hash = _ocr().compute_file_hash(contents)

            pending_docs.append(
                {
                    "file_name": clean_filename,
                    "file_type": ftype,
                    "file_path": rel_path,
                    "file_hash": _ocr().compute_file_hash(contents),
                    "extracted": extracted,
                }
            )

        def _persist_documents() -> None:
            for item in pending_docs:
                document = Document(
                    doc_id=next_doc_id(db),
                    claim_id=claim_id,
                    product_id=product.product_id,
                    user_id=user.user_id,
                    file_name=item["file_name"],
                    file_type=item["file_type"],
                    file_path=item["file_path"],
                    file_hash=item["file_hash"],
                    extracted_data_json=json.dumps(item["extracted"]) if item["extracted"] else None,
                )
                db.add(document)
                db.flush()
                write_audit(
                    db,
                    action="Document Upload",
                    performed_by=user.user_id,
                    user_id=user.user_id,
                    claim_id=claim_id,
                    entity_type="document",
                    entity_id=document.doc_id,
                    details={"file_type": item["file_type"], "hash": item["file_hash"]},
                )

        def _attach_existing(doc_ids: str) -> None:
            for doc_id in [x.strip() for x in (doc_ids or "").split(",") if x.strip()]:
                existing = (
                    scoped_documents(db, user)
                    .filter(Document.doc_id == doc_id)
                    .first()
                )
                if existing:
                    existing.claim_id = claim_id
                    existing.product_id = product.product_id

        # ------------------------------------------------------------ #
        # 4a. Draft branch
        # ------------------------------------------------------------ #
        if is_draft:
            if db_claim is None:
                db_claim = Claim(
                    claim_id=claim_id,
                    user_id=user.user_id,
                    product_id=product.product_id,
                    fault_category=payload.get("fault_category") or "motherboard_failure",
                    damage_type=payload.get("damage_type") or "none",
                    fault_occurrence_date=fault_occurrence_date,
                    claim_submission_date=claim_submission_date,
                    description=payload.get("description") or "",
                    status="Draft",
                    final_decision="Draft",
                    decision_explanation_json=json.dumps({"notes": "Claim saved as draft."}),
                    document_hash=file_hash,
                    extended_warranty_provider=(payload.get("extended_warranty_provider") or "").strip()
                    or getattr(product, "extended_warranty_provider", ""),
                    extended_warranty_contract_number=(payload.get("extended_warranty_contract_number") or "").strip()
                    or getattr(product, "extended_warranty_contract_number", ""),
                    model_version=str(get("model_version", "v2")),
                )
                db.add(db_claim)
            else:
                db_claim.product_id = product.product_id
                db_claim.fault_category = payload.get("fault_category") or "motherboard_failure"
                db_claim.damage_type = payload.get("damage_type") or "none"
                db_claim.fault_occurrence_date = fault_occurrence_date
                db_claim.claim_submission_date = claim_submission_date
                db_claim.description = payload.get("description") or ""
                record_status_transition(
                    db,
                    db_claim,
                    "Draft",
                    actor_user_id=user.user_id,
                    actor_role=user.role,
                    note="Draft saved",
                )
                db_claim.final_decision = "Draft"
                if (payload.get("extended_warranty_provider") or "").strip():
                    db_claim.extended_warranty_provider = payload["extended_warranty_provider"].strip()
                if (payload.get("extended_warranty_contract_number") or "").strip():
                    db_claim.extended_warranty_contract_number = payload["extended_warranty_contract_number"].strip()

            db.flush()
            ensure_initial_status(
                db,
                db_claim,
                actor_user_id=user.user_id,
                actor_role=user.role,
                note="Draft saved",
            )
            _persist_documents()
            _attach_existing(payload.get("attach_doc_ids") or "")
            write_audit(
                db,
                action="Claim Draft Saved",
                performed_by=user.user_id,
                user_id=user.user_id,
                claim_id=claim_id,
                entity_type="claim",
                entity_id=claim_id,
                details={"status": "Draft"},
            )
            db.commit()
            return db_claim

        # ------------------------------------------------------------ #
        # 4b. Full adjudication
        # ------------------------------------------------------------ #
        present_keys = documents_by_policy_key(
            db.query(Document).filter(Document.product_id == product.product_id).all()
        )
        for item in pending_docs:
            present_keys.add(item["file_type"])
            present_keys.add(FILE_TYPE_MAP.get(item["file_type"], item["file_type"]))

        policy = load_policy(product.category)
        missing_mandatory = [
            doc for doc in policy.get("mandatory_documents", []) if doc not in present_keys
        ]

        prev_count, has_unauth = repair_stats_for_product(db, product.product_id)
        ext_provider = (
            (payload.get("extended_warranty_provider") or "").strip()
            or getattr(product, "extended_warranty_provider", "")
        )
        ext_contract = (
            (payload.get("extended_warranty_contract_number") or "").strip()
            or getattr(product, "extended_warranty_contract_number", "")
        )
        ext_months = int(
            payload.get("extended_warranty_duration_months")
            or getattr(product, "extended_warranty_duration_months", 0)
            or 0
        )

        raw_payload = product_to_claim_dict(product)
        raw_payload.update(
            {
                "claim_id": claim_id,
                "user_id": user.user_id,
                "fault_occurrence_date": fault_occurrence_date,
                "claim_submission_date": claim_submission_date,
                "fault_category": payload.get("fault_category") or "motherboard_failure",
                "damage_type": payload.get("damage_type") or "none",
                "description": payload.get("description") or "",
                "ocr_serial_number": ocr_extracted.get("extracted_serial_number")
                or product.serial_number,
                "document_hash": file_hash,
                "has_receipt": "purchase_receipt" in present_keys,
                "has_warranty_card": "warranty_card" in present_keys,
                "has_product_photo": "product_image" in present_keys,
                "has_serial_photo": "serial_number_photo" in present_keys,
                "missing_documents_count": len(missing_mandatory),
                "previous_repairs_count": payload.get("previous_repairs_count")
                if payload.get("previous_repairs_count") is not None
                else prev_count,
                "has_unauthorized_repairs": _as_bool(payload.get("has_unauthorized_repairs"))
                or has_unauth,
                "has_extended_warranty": _as_bool(payload.get("has_extended_warranty"))
                or bool(ext_provider or ext_contract or ext_months > 0)
                or bool(getattr(product, "has_extended_warranty", False)),
                "extended_warranty_provider": ext_provider,
                "extended_warranty_contract_number": ext_contract,
                "extended_warranty_duration_months": ext_months,
            }
        )

        claim_dict = compute_derived_claim_features(raw_payload)

        started_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Model inference
        py_result = registry.tabular.predict_single(claim_dict)
        card_img = render_claim_card(pd.Series(claim_dict), variation_id=1)
        card_path = uploads_dir() / f"{claim_id}_summary_card.png"
        card_img.save(card_path)
        vis_result = registry.vision.predict_image(card_img)

        existing_claims_db = [c.__dict__ for c in db.query(Claim).all()]
        dossier = registry.fusion.evaluate_full_claim(
            claim_dict, py_result, vis_result, existing_claims_db
        )

        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        comparison = dossier["comparison"]
        final_decision = dossier["final_decision"]
        model_version = str(get("model_version", "v2"))

        if final_decision == "Manual Review Required":
            claim_status = "Manual Review"
        elif final_decision == "Likely Valid":
            claim_status = "Approved"
        else:
            claim_status = "Rejected"

        claim_fields = dict(
            product_id=product.product_id,
            fault_category=payload.get("fault_category") or "motherboard_failure",
            damage_type=payload.get("damage_type") or "none",
            fault_occurrence_date=fault_occurrence_date,
            claim_submission_date=claim_submission_date,
            description=payload.get("description") or "",
            python_predicted_class=py_result["predicted_class"],
            python_top_confidence=py_result["top_confidence"],
            vision_predicted_class=vis_result["predicted_class"],
            vision_top_confidence=vis_result["top_confidence"],
            confidence_difference=comparison["confidence_difference"],
            consistency_status=comparison["consistency_status"],
            final_decision=final_decision,
            decision_explanation_json=json.dumps(dossier, default=str),
            document_hash=file_hash,
            extended_warranty_provider=ext_provider,
            extended_warranty_contract_number=ext_contract,
            model_version=model_version,
        )

        if db_claim is None:
            db_claim = Claim(claim_id=claim_id, user_id=user.user_id, status="Draft", **claim_fields)
            db.add(db_claim)
        else:
            for key, value in claim_fields.items():
                setattr(db_claim, key, value)

        db.flush()
        record_submission_stages(
            db,
            db_claim,
            claim_status,
            started_at=started_at,
            finished_at=finished_at,
            actor_user_id=user.user_id,
            actor_role=user.role,
        )
        _persist_documents()
        _attach_existing(payload.get("attach_doc_ids") or "")

        write_audit(
            db,
            action="AI Inference",
            performed_by=user.user_id,
            user_id=user.user_id,
            claim_id=claim_id,
            entity_type="claim",
            entity_id=claim_id,
            details={"final_decision": final_decision, "model_version": model_version},
        )
        write_audit(
            db,
            action="Status Change",
            performed_by="system",
            user_id=user.user_id,
            claim_id=claim_id,
            entity_type="claim",
            entity_id=claim_id,
            details={"status": claim_status},
        )
        write_audit(
            db,
            action="Alert Claimed",
            performed_by=user.user_id,
            user_id=user.user_id,
            claim_id=claim_id,
            entity_type="product",
            entity_id=product.product_id,
            details={"via": "claim_submit"},
        )
        db.commit()
        try:
            notification_service.after_claim_submitted(
                db_claim, missing_documents=len(missing_mandatory)
            )
        except Exception as exc:  # notifications must never break a claim
            print(f"[notifications] claim {claim_id} notification failed: {exc}", flush=True)
        return db_claim

    except HttpError:
        db.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive rollback
        db.rollback()
        raise HttpError(500, f"Error submitting claim: {exc}") from exc


# --------------------------------------------------------------------------- #
# Pre-check (no model inference, policy + contradiction evaluation only)
# --------------------------------------------------------------------------- #
def precheck(db: Session, user: User, data: dict) -> dict:
    product = (
        scoped_products(db, user)
        .filter(Product.product_id == (data.get("product_id") or "").strip())
        .first()
    )
    if product is None:
        raise HttpError(400, "Select a registered product first.")

    submit_date = (data.get("claim_submission_date") or "").strip() or _today()
    docs = db.query(Document).filter(Document.product_id == product.product_id).all()
    present = documents_by_policy_key(docs)
    policy = load_policy(product.category)
    missing = [m for m in policy.get("mandatory_documents", []) if m not in present]

    prev_count, has_unauth = repair_stats_for_product(db, product.product_id)
    raw = product_to_claim_dict(product)
    raw.update(
        {
            "fault_occurrence_date": data.get("fault_occurrence_date"),
            "claim_submission_date": submit_date,
            "fault_category": data.get("fault_category") or "general_defect",
            "damage_type": data.get("damage_type") or "none",
            "previous_repairs_count": prev_count,
            "has_unauthorized_repairs": has_unauth,
            "has_receipt": "purchase_receipt" in present or "receipt" in present,
            "has_warranty_card": "warranty_card" in present,
            "has_product_photo": "product_image" in present,
            "has_serial_photo": "serial_number_photo" in present,
            "missing_documents_count": len(missing),
        }
    )

    derived = compute_derived_claim_features(raw)

    from assurex_claim_engine.decision.contradiction import (
        ContradictionAndDuplicateDetector,
    )
    from assurex_claim_engine.rule_engine.evaluator import PolicyRuleEvaluator

    contradictions = ContradictionAndDuplicateDetector.detect_contradictions(derived)
    rule_eval = PolicyRuleEvaluator().evaluate_claim(derived)
    warnings = list(rule_eval.get("warnings") or [])
    if derived.get("remaining_warranty_days", 0) <= int(get("warranty_alert_days", 30)):
        warnings.append("Warranty is expired, in grace, or inside the alert window.")

    actions = []
    if missing:
        actions.append(f"Upload missing documents: {', '.join(missing)}")
    if contradictions["has_contradictions"]:
        actions.extend(contradictions["contradictions"])

    return {
        "ready": not missing and not contradictions["has_contradictions"],
        "missing_documents": missing,
        "warnings": warnings,
        "contradictions": contradictions["contradictions"],
        "recommended_actions": actions,
        "remaining_warranty_days": derived.get("remaining_warranty_days"),
        "serial_match_status": derived.get("serial_match_status"),
    }


# --------------------------------------------------------------------------- #
# CSV bulk import
# --------------------------------------------------------------------------- #
def import_claims_csv(db: Session, user: User, contents: bytes) -> dict:
    try:
        registry.ensure_ready()
    except ModelNotReady as exc:
        raise HttpError(503, str(exc)) from exc

    try:
        frame = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HttpError(400, f"Failed to parse CSV file: {exc}") from exc

    imported = 0
    errors: list[dict] = []
    now_tag = datetime.now().strftime("%m%d%H%M%S")

    for idx, row in frame.iterrows():
        try:
            raw_claim_id = str(row.get("claim_id", "")).strip()
            if (
                not raw_claim_id
                or raw_claim_id.lower() == "nan"
                or db.query(Claim).filter(Claim.claim_id == raw_claim_id).first()
            ):
                claim_id = f"CLM-{now_tag}-{idx:04d}"
            else:
                claim_id = raw_claim_id

            raw_product_id = str(row.get("product_id", "")).strip()
            if (
                not raw_product_id
                or raw_product_id.lower() == "nan"
                or db.query(Product).filter(Product.product_id == raw_product_id).first()
            ):
                product_id = f"PRD-{now_tag}-{idx:04d}"
            else:
                product_id = raw_product_id

            raw_user_id = str(row.get("user_id", "")).strip()
            if (
                raw_user_id
                and raw_user_id.lower() != "nan"
                and db.query(User).filter(User.user_id == raw_user_id).first()
            ):
                row_user_id = raw_user_id
            else:
                row_user_id = user.user_id

            product_name = str(row.get("product_name", "Warranty Product"))
            product_category = str(row.get("product_category", "electronics"))
            brand = str(row.get("brand", "Generic"))
            model_number = str(row.get("model_number", "MOD-100"))
            serial_number = str(
                row.get("user_serial_number", row.get("serial_number", f"SN-{now_tag}-{idx:04d}"))
            )
            ocr_serial = str(row.get("ocr_serial_number", serial_number))
            purchase_date = str(row.get("purchase_date", "2024-01-01"))
            try:
                purchase_price = float(row.get("purchase_price", 500.0))
            except Exception:
                purchase_price = 500.0
            retailer = str(row.get("retailer", "Retailer Store"))
            try:
                warranty_months = int(row.get("warranty_duration_months", 24))
            except Exception:
                warranty_months = 24

            fault_category = str(row.get("fault_category", "Hardware Defect"))
            damage_type = str(row.get("damage_type", "none"))
            fault_occurrence_date = str(row.get("fault_occurrence_date", "2025-05-01"))
            claim_submission_date = str(row.get("claim_submission_date", _today()))
            description = str(row.get("description", "Imported claim record from CSV"))
            try:
                prev_repairs = int(row.get("previous_repairs_count", 0) or 0)
            except Exception:
                prev_repairs = 0
            has_unauth = str(row.get("has_unauthorized_repairs", False)).strip().lower() in (
                "true",
                "1",
                "yes",
            )

            row_dict = row.to_dict()
            row_dict.update(
                {
                    "claim_id": claim_id,
                    "user_id": row_user_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "product_category": product_category,
                    "brand": brand,
                    "model_number": model_number,
                    "user_serial_number": serial_number,
                    "ocr_serial_number": ocr_serial,
                    "purchase_date": purchase_date,
                    "purchase_price": purchase_price,
                    "retailer": retailer,
                    "warranty_duration_months": warranty_months,
                    "fault_occurrence_date": fault_occurrence_date,
                    "claim_submission_date": claim_submission_date,
                    "fault_category": fault_category,
                    "damage_type": damage_type,
                    "previous_repairs_count": prev_repairs,
                    "has_unauthorized_repairs": has_unauth,
                }
            )
            claim_dict = compute_derived_claim_features(row_dict)

            py_result = registry.tabular.predict_single(claim_dict)
            card_img = render_claim_card(pd.Series(claim_dict), variation_id=1)
            card_img.save(uploads_dir() / f"{claim_id}_summary_card.png")
            vis_result = registry.vision.predict_image(card_img)

            existing_claims_db = [c.__dict__ for c in db.query(Claim).all()]
            dossier = registry.fusion.evaluate_full_claim(
                claim_dict, py_result, vis_result, existing_claims_db
            )
            comparison = dossier["comparison"]
            final_decision = dossier["final_decision"]

            db.add(
                Product(
                    product_id=product_id,
                    user_id=row_user_id,
                    product_name=product_name,
                    category=product_category,
                    brand=brand,
                    model_number=model_number,
                    serial_number=serial_number,
                    purchase_date=purchase_date,
                    purchase_price=purchase_price,
                    retailer=retailer,
                    warranty_duration_months=warranty_months,
                )
            )
            db_claim = Claim(
                claim_id=claim_id,
                user_id=row_user_id,
                product_id=product_id,
                fault_category=fault_category,
                damage_type=damage_type,
                fault_occurrence_date=fault_occurrence_date,
                claim_submission_date=claim_submission_date,
                description=description,
                status="Draft",
                python_predicted_class=py_result["predicted_class"],
                    python_top_confidence=py_result["top_confidence"],
                    vision_predicted_class=vis_result["predicted_class"],
                    vision_top_confidence=vis_result["top_confidence"],
                    confidence_difference=comparison["confidence_difference"],
                    consistency_status=comparison["consistency_status"],
                    final_decision=final_decision,
                    decision_explanation_json=json.dumps(dossier, default=str),
                    model_version=str(get("model_version", "v2")),
            )
            db.add(db_claim)
            db.flush()
            record_submission_stages(
                db,
                db_claim,
                "Manual Review" if final_decision == "Manual Review Required" else ("Approved" if final_decision == "Likely Valid" else "Rejected"),
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
                actor_user_id=row_user_id,
                actor_role=user.role,
            )
            db.commit()
            imported += 1
        except Exception as row_err:  # pragma: no cover - per-row resilience
            db.rollback()
            errors.append({"row": int(idx), "error": str(row_err)})
            continue

    return {"imported_count": imported, "errors": errors, "total_rows": int(len(frame))}
