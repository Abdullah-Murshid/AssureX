"""Claim status transition helpers.

Every status write must go through :func:`record_status_transition` so the
timeline cannot drift from ``claims.status``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .database import Claim, ClaimStatusHistory, SessionLocal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def record_status_transition(
    db: Session,
    claim: Claim,
    to_status: str,
    *,
    actor_user_id: Optional[str] = None,
    actor_role: str = "system",
    note: str = "",
    from_status: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Optional[ClaimStatusHistory]:
    """Record one transition and update the claim's current status."""
    current = claim.status if from_status is None else from_status
    if current == to_status:
        return None

    row = ClaimStatusHistory(
        claim_id=claim.claim_id,
        from_status=current,
        to_status=to_status,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note=note or None,
        created_at=created_at or _utcnow(),
    )
    claim.status = to_status
    db.add(row)
    return row


def ensure_initial_status(
    db: Session,
    claim: Claim,
    *,
    actor_user_id: Optional[str] = None,
    actor_role: str = "system",
    note: str = "Claim created",
    created_at: Optional[datetime] = None,
) -> Optional[ClaimStatusHistory]:
    """Write a single baseline row for a claim that has no history yet."""
    existing = (
        db.query(ClaimStatusHistory.id)
        .filter(ClaimStatusHistory.claim_id == claim.claim_id)
        .first()
    )
    if existing:
        return None
    status = claim.status or "Draft"
    row = ClaimStatusHistory(
        claim_id=claim.claim_id,
        from_status=None,
        to_status=status,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note=note,
        created_at=created_at or _utcnow(),
    )
    db.add(row)
    return row


def record_submission_stages(
    db: Session,
    claim: Claim,
    final_status: str,
    *,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    actor_user_id: Optional[str] = None,
    actor_role: str = "system",
) -> None:
    """Write Draft -> Submitted -> Under Evaluation -> final status in order."""
    started = started_at or _utcnow()
    finished = finished_at or _utcnow()

    ensure_initial_status(
        db,
        claim,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note="Claim created",
        created_at=started,
    )
    record_status_transition(
        db,
        claim,
        "Submitted",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note="Claim submitted",
        created_at=started,
    )
    record_status_transition(
        db,
        claim,
        "Under Evaluation",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note="Dual-model evaluation started",
        created_at=started + timedelta(milliseconds=1),
    )
    record_status_transition(
        db,
        claim,
        final_status,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        note=f"Final decision: {claim.final_decision or final_status}",
        created_at=max(finished, started + timedelta(milliseconds=2)),
    )


def backfill_claim_status_history() -> int:
    """Idempotently give legacy claims one synthetic, migrated history row."""
    db = SessionLocal()
    try:
        existing_ids = {
            row[0]
            for row in db.query(ClaimStatusHistory.claim_id).distinct().all()
            if row[0]
        }
        created = 0
        for claim in db.query(Claim).all():
            if claim.claim_id in existing_ids:
                continue
            db.add(
                ClaimStatusHistory(
                    claim_id=claim.claim_id,
                    from_status=None,
                    to_status=claim.status or "Unknown",
                    actor_user_id=None,
                    actor_role="system",
                    note="Migrated from existing claim status.",
                    created_at=claim.created_at or _utcnow(),
                )
            )
            created += 1
        if created:
            db.commit()
            print(f"[migrate] Backfilled status history for {created} claim(s).", flush=True)
        return created
    except Exception as exc:  # pragma: no cover - startup must not fail
        db.rollback()
        print(f"[migrate] Status-history backfill skipped: {exc}", flush=True)
        return 0
    finally:
        db.close()
