from __future__ import annotations

from ninja import Router
from ninja.errors import HttpError

from assurex_claim_engine.db.database import Notification
from assurex_claim_engine.notifications import ensure_warranty_expiry_notifications
from assurex_claim_engine.web.helpers import paginate

from ..deps import auth, current_principal, db_of
from ..serializers import notification_out

router = Router(tags=["Notifications"], auth=auth)


@router.get("/notifications")
def list_notifications(
    request,
    unread: bool = False,
    page: int = 1,
    per_page: int = 20,
):
    principal = current_principal(request)
    db = db_of(request)
    ensure_warranty_expiry_notifications(principal.user_id)

    query = db.query(Notification).filter(Notification.user_id == principal.user_id)
    if unread:
        query = query.filter(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc(), Notification.id.desc())
    pagination = paginate(query, page=page, per_page=per_page)
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == principal.user_id, Notification.is_read.is_(False))
        .count()
    )
    return {
        "items": [notification_out(row) for row in pagination["items"]],
        "page": pagination["page"],
        "per_page": pagination["per_page"],
        "total": pagination["total"],
        "total_pages": pagination["total_pages"],
        "unread": unread_count,
    }


@router.get("/notifications/unread-count")
def unread_count(request):
    principal = current_principal(request)
    db = db_of(request)
    ensure_warranty_expiry_notifications(principal.user_id)
    count = (
        db.query(Notification)
        .filter(Notification.user_id == principal.user_id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.post("/notifications/read-all")
def read_all(request):
    principal = current_principal(request)
    db = db_of(request)
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == principal.user_id, Notification.is_read.is_(False))
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"updated": int(updated)}


@router.post("/notifications/{notification_id}/read")
def mark_read(request, notification_id: int):
    principal = current_principal(request)
    db = db_of(request)
    row = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == principal.user_id,
        )
        .first()
    )
    if row is None:
        raise HttpError(404, "Notification not found.")
    row.is_read = True
    db.commit()
    db.refresh(row)
    return notification_out(row)
