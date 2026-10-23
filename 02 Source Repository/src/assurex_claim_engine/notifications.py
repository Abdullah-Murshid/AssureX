"""Notification creation helpers.

All writes use a short-lived session and swallow failures: a notification must
never abort a claim, review or warranty operation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config.settings_loader import get

from .db.database import Claim, Notification, Product, SessionLocal, User
from .web.helpers import enrich_product

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notify_user(
    user_id: str,
    type: str,
    title: str,
    message: str,
    *,
    claim_id: Optional[str] = None,
    product_id: Optional[str] = None,
) -> bool:
    """Create one notification; failures are logged and ignored."""
    if not user_id:
        return False
    try:
        db = SessionLocal()
        try:
            db.add(
                Notification(
                    user_id=user_id,
                    type=type,
                    title=title,
                    message=message,
                    claim_id=claim_id,
                    product_id=product_id,
                )
            )
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to create notification type=%s user=%s", type, user_id)
        return False


def notify_reviewers(
    title: str,
    message: str,
    *,
    claim_id: Optional[str] = None,
    product_id: Optional[str] = None,
) -> int:
    """Notify every reviewer account; never raises."""
    try:
        db = SessionLocal()
        try:
            reviewer_ids = [
                row[0]
                for row in db.query(User.user_id).filter(User.role == "reviewer").all()
            ]
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to load reviewers for notification")
        return 0
    return sum(
        1
        for user_id in reviewer_ids
        if notify_user(
            user_id,
            "manual_review_assigned",
            title,
            message,
            claim_id=claim_id,
            product_id=product_id,
        )
    )


def after_claim_submitted(claim: Claim, *, missing_documents: int = 0) -> None:
    """Claimant + reviewer notifications for a completed submission."""
    claimant = claim.user_id
    claim_ref = claim.claim_id
    product_ref = claim.product_id
    decision = claim.final_decision or ""

    notify_user(
        claimant,
        "claim_submitted",
        "Claim submitted",
        f"Your claim {claim_ref} was submitted successfully.",
        claim_id=claim_ref,
        product_id=product_ref,
    )

    if missing_documents:
        notify_user(
            claimant,
            "missing_documents",
            "Documents required",
            f"Claim {claim_ref} is missing {missing_documents} mandatory document(s).",
            claim_id=claim_ref,
            product_id=product_ref,
        )

    if decision == "Manual Review Required":
        notify_user(
            claimant,
            "manual_review",
            "Claim sent for manual review",
            f"Claim {claim_ref} needs a reviewer because the automated checks were not conclusive.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
        notify_reviewers(
            "Claim entered manual review",
            f"Claim {claim_ref} is waiting for a reviewer decision.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
        notify_user(
            claimant,
            "claim_status",
            "Claim status: Manual Review",
            f"Claim {claim_ref} is now in manual review.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
    elif decision == "Likely Valid":
        notify_user(
            claimant,
            "claim_approved",
            "Claim approved",
            f"Claim {claim_ref} was approved as a likely valid claim.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
        notify_user(
            claimant,
            "claim_status",
            "Claim status: Approved",
            f"Claim {claim_ref} is now Approved.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
    else:
        notify_user(
            claimant,
            "claim_rejected",
            "Claim rejected",
            f"Claim {claim_ref} was rejected by the automated assessment.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
        notify_user(
            claimant,
            "claim_status",
            "Claim status: Rejected",
            f"Claim {claim_ref} is now Rejected.",
            claim_id=claim_ref,
            product_id=product_ref,
        )


def after_review_action(claim: Claim, action: str, comments: str = "") -> None:
    """Claimant notifications for a reviewer decision."""
    claimant = claim.user_id
    claim_ref = claim.claim_id
    product_ref = claim.product_id

    notify_user(
        claimant,
        "review_completed",
        "Review completed",
        f"A reviewer completed the review of claim {claim_ref}.",
        claim_id=claim_ref,
        product_id=product_ref,
    )
    notify_user(
        claimant,
        "claim_status",
        f"Claim status: {action}",
        f"Claim {claim_ref} is now {action}.",
        claim_id=claim_ref,
        product_id=product_ref,
    )

    if action == "Request More Info":
        notify_user(
            claimant,
            "additional_info_requested",
            "Additional information requested",
            comments or f"More information is required for claim {claim_ref}.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
    elif action == "Approved":
        notify_user(
            claimant,
            "claim_approved",
            "Claim approved",
            f"Claim {claim_ref} was approved by a reviewer.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
    elif action == "Rejected":
        notify_user(
            claimant,
            "claim_rejected",
            "Claim rejected",
            f"Claim {claim_ref} was rejected by a reviewer.",
            claim_id=claim_ref,
            product_id=product_ref,
        )
    elif action == "Closed":
        notify_user(
            claimant,
            "claim_closed",
            "Claim closed",
            f"Claim {claim_ref} was closed.",
            claim_id=claim_ref,
            product_id=product_ref,
        )


def ensure_warranty_expiry_notifications(user_id: str) -> int:
    """Create at most one warranty-expiry notification per product per window."""
    try:
        db = SessionLocal()
        try:
            alert_days = int(get("warranty_alert_days", 30) or 30)
            cutoff = _utcnow() - timedelta(days=alert_days)
            products = db.query(Product).filter(Product.user_id == user_id).all()
            created = 0
            for product in products:
                row = enrich_product(product)
                remaining = row.get("remaining_warranty_days")
                if remaining is None or remaining < 0 or remaining > alert_days:
                    continue
                duplicate = (
                    db.query(Notification.id)
                    .filter(
                        Notification.user_id == user_id,
                        Notification.type == "warranty_expiry",
                        Notification.product_id == product.product_id,
                        Notification.created_at >= cutoff,
                    )
                    .first()
                )
                if duplicate:
                    continue
                db.add(
                    Notification(
                        user_id=user_id,
                        type="warranty_expiry",
                        title="Warranty expiring soon",
                        message=(
                            f"{product.product_name} ({product.serial_number}) expires on "
                            f"{row.get('warranty_expiry_date')} — {remaining} day(s) left."
                        ),
                        product_id=product.product_id,
                    )
                )
                created += 1
            if created:
                db.commit()
            return created
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to generate warranty expiry notifications for %s", user_id)
        return 0
