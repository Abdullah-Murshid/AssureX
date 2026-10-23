"""Tests for claim status history (FR-xxxviii) and notifications (FR-xxxix)."""

from __future__ import annotations

import json
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from assurex_claim_engine.db.database import Claim, ClaimStatusHistory, SessionLocal
from assurex_claim_engine.db.status_history import backfill_claim_status_history

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _login(client: Client, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


def _product(
    client: Client,
    headers: dict,
    *,
    purchase_date: str = "2025-06-01",
    months: int = 24,
    serial: str | None = None,
) -> str:
    response = client.post(
        "/api/v1/products",
        data=json.dumps(
            {
                "product_name": "History Laptop",
                "category": "electronics",
                "brand": "HistoryBrand",
                "model_number": "H-1",
                "serial_number": serial or f"H-{uuid.uuid4().hex[:10]}",
                "purchase_date": purchase_date,
                "purchase_price": 1000.0,
                "retailer": "History Retailer",
                "warranty_duration_months": months,
            }
        ),
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 201, response.content
    return response.json()["product"]["product_id"]


def _upload(client: Client, headers: dict, product_id: str):
    response = None
    for file_type in ("purchase_receipt", "warranty_card"):
        response = client.post(
            "/api/v1/documents",
            data={
                "file_type": file_type,
                "product_id": product_id,
                "upload": SimpleUploadedFile(f"{file_type}.png", PNG_BYTES, content_type="image/png"),
            },
            **headers,
        )
    return response


def _submit(
    client: Client,
    headers: dict,
    product_id: str,
    *,
    draft: bool = False,
    occurrence: str = "2026-10-01",
):
    return client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "fault_category": "motherboard_failure",
            "damage_type": "none",
            "fault_occurrence_date": occurrence,
            "claim_submission_date": "2026-10-23",
            "description": "History and notification test",
            "action_type": "draft" if draft else "submit",
        },
        **headers,
    )


def _history(client: Client, headers: dict, claim_id: str):
    response = client.get(f"/api/v1/claims/{claim_id}/history", **headers)
    assert response.status_code == 200, response.content
    return response.json()["history"]


def test_submitted_claim_writes_full_status_timeline(client, customer_headers, models_ready):
    product_id = _product(client, customer_headers)
    _upload(client, customer_headers, product_id)
    claim = _submit(client, customer_headers, product_id)
    assert claim.status_code == 201, claim.content
    body = claim.json()
    history = _history(client, customer_headers, body["claim_id"])
    statuses = [row["to_status"] for row in history]
    assert statuses[0] == "Draft"
    assert "Submitted" in statuses
    assert "Under Evaluation" in statuses
    assert statuses[-1] == body["status"]
    assert all(row["actor_user_id"] == "USR-0001" for row in history[1:])

    # Final status is unchanged from the pre-history behaviour.
    assert body["status"] in {"Approved", "Rejected", "Manual Review"}

    notifications = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()
    types = {row["type"] for row in notifications["items"] if row["claim_id"] == body["claim_id"]}
    assert "claim_submitted" in types
    assert "claim_approved" in types


def test_draft_then_submit_records_transition(client, customer_headers, models_ready):
    product_id = _product(client, customer_headers)
    _upload(client, customer_headers, product_id)
    draft = _submit(client, customer_headers, product_id, draft=True)
    assert draft.status_code == 201, draft.content
    draft_id = draft.json()["claim_id"]
    assert [row["to_status"] for row in _history(client, customer_headers, draft_id)] == ["Draft"]

    submitted = client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "draft_id": draft_id,
            "fault_category": "motherboard_failure",
            "damage_type": "none",
            "fault_occurrence_date": "2026-10-01",
            "claim_submission_date": "2026-10-23",
            "description": "Draft resubmitted",
            "action_type": "submit",
        },
        **customer_headers,
    )
    assert submitted.status_code == 201, submitted.content
    statuses = [row["to_status"] for row in _history(client, customer_headers, draft_id)]
    assert statuses[0] == "Draft"
    assert statuses[1] == "Submitted"
    assert statuses[2] == "Under Evaluation"
    assert statuses[-1] == submitted.json()["status"]


def test_reviewer_override_writes_transition_and_notifies(client, customer_headers, reviewer_headers):
    product_id = _product(client, customer_headers, purchase_date="2023-01-01", months=12)
    _upload(client, customer_headers, product_id)
    claim = _submit(client, customer_headers, product_id)
    assert claim.status_code == 201, claim.content
    body = claim.json()
    assert body["status"] == "Manual Review"

    decision = client.post(
        f"/api/v1/review/{body['claim_id']}/decision",
        data=json.dumps(
            {"action": "Request More Info", "comments": "Please upload the invoice."}
        ),
        content_type="application/json",
        **reviewer_headers,
    )
    assert decision.status_code == 200, decision.content

    statuses = [row["to_status"] for row in _history(client, customer_headers, body["claim_id"])]
    assert "Manual Review" in statuses
    assert statuses[-1] == "Request More Info"
    assert any(row["actor_role"] == "reviewer" for row in _history(client, customer_headers, body["claim_id"]))

    notifications = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()
    types = {row["type"] for row in notifications["items"] if row["claim_id"] == body["claim_id"]}
    assert "additional_info_requested" in types
    assert "review_completed" in types

    rejected = client.post(
        f"/api/v1/review/{body['claim_id']}/decision",
        data=json.dumps({"action": "Rejected", "comments": "Invoice does not match the product."}),
        content_type="application/json",
        **reviewer_headers,
    )
    assert rejected.status_code == 200, rejected.content
    rejected_types = {
        row["type"]
        for row in client.get("/api/v1/notifications?per_page=100", **customer_headers).json()["items"]
        if row["claim_id"] == body["claim_id"]
    }
    assert "claim_rejected" in rejected_types


def test_history_access_is_owner_or_staff_only(client, customer_headers):
    product_id = _product(client, customer_headers)
    claim = _submit(client, customer_headers, product_id, draft=True)
    claim_id = claim.json()["claim_id"]

    other = client.post(
        "/api/v1/auth/register",
        data=json.dumps(
            {
                "full_name": "Other History User",
                "email": f"history.{uuid.uuid4().hex[:8]}@example.com",
                "password": "verysecret123",
                "role": "customer",
            }
        ),
        content_type="application/json",
    )
    other_headers = {"HTTP_AUTHORIZATION": f"Bearer {other.json()['access_token']}"}
    assert client.get(f"/api/v1/claims/{claim_id}/history", **other_headers).status_code == 403


def test_notifications_are_own_only_and_read_work(client, customer_headers):
    first = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()
    assert first["items"]
    target = first["items"][0]

    other = client.post(
        "/api/v1/auth/register",
        data=json.dumps(
            {
                "full_name": "Other Notification User",
                "email": f"notify.{uuid.uuid4().hex[:8]}@example.com",
                "password": "verysecret123",
                "role": "customer",
            }
        ),
        content_type="application/json",
    )
    other_headers = {"HTTP_AUTHORIZATION": f"Bearer {other.json()['access_token']}"}
    assert client.get("/api/v1/notifications", **other_headers).json()["items"] == []
    assert client.post(f"/api/v1/notifications/{target['id']}/read", **other_headers).status_code == 404

    unread_before = client.get("/api/v1/notifications/unread-count", **customer_headers).json()["count"]
    marked = client.post(f"/api/v1/notifications/{target['id']}/read", **customer_headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert client.get("/api/v1/notifications/unread-count", **customer_headers).json()["count"] <= unread_before

    read_all = client.post("/api/v1/notifications/read-all", **customer_headers)
    assert read_all.status_code == 200
    assert client.get("/api/v1/notifications/unread-count", **customer_headers).json()["count"] == 0
    assert client.get("/api/v1/notifications?unread=true", **customer_headers).json()["items"] == []


def test_manual_review_notifies_reviewers(client, customer_headers, reviewer_headers):
    product_id = _product(client, customer_headers, purchase_date="2023-01-01", months=12)
    _upload(client, customer_headers, product_id)
    claim = _submit(client, customer_headers, product_id)
    assert claim.json()["status"] == "Manual Review"

    reviewer_items = client.get("/api/v1/notifications?per_page=100", **reviewer_headers).json()["items"]
    assert any(
        row["type"] == "manual_review_assigned" and row["claim_id"] == claim.json()["claim_id"]
        for row in reviewer_items
    )


def test_warranty_notification_is_deduplicated_per_window(client, customer_headers):
    product_id = _product(
        client,
        customer_headers,
        purchase_date="2024-11-15",
        months=24,
        serial=f"W-{uuid.uuid4().hex[:10]}",
    )
    first = client.get("/api/v1/notifications/unread-count", **customer_headers)
    assert first.status_code == 200

    items = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()["items"]
    warranty = [row for row in items if row["type"] == "warranty_expiry" and row["product_id"] == product_id]
    assert warranty

    client.get("/api/v1/notifications/unread-count", **customer_headers)
    items_again = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()["items"]
    assert len([row for row in items_again if row["type"] == "warranty_expiry" and row["product_id"] == product_id]) == 1


def test_backfill_is_idempotent_and_labels_migrated(client, customer_headers):
    product_id = _product(client, customer_headers)
    claim = _submit(client, customer_headers, product_id, draft=True)
    claim_id = claim.json()["claim_id"]

    with SessionLocal() as db:
        db.query(ClaimStatusHistory).filter(ClaimStatusHistory.claim_id == claim_id).delete()
        db.commit()

    assert backfill_claim_status_history() >= 1
    assert backfill_claim_status_history() == 0

    with SessionLocal() as db:
        rows = db.query(ClaimStatusHistory).filter(ClaimStatusHistory.claim_id == claim_id).all()
    assert len(rows) == 1
    assert rows[0].actor_role == "system"
    assert "Migrated" in (rows[0].note or "")


def test_init_db_twice_is_safe(client, customer_headers):
    from assurex_claim_engine.db.database import init_db

    product_id = _product(client, customer_headers)
    claim = _submit(client, customer_headers, product_id, draft=True)
    claim_id = claim.json()["claim_id"]

    init_db()
    init_db()
    with SessionLocal() as db:
        rows = db.query(ClaimStatusHistory).filter(ClaimStatusHistory.claim_id == claim_id).all()
    assert len(rows) == 1


def test_notification_failure_is_swallowed(monkeypatch):
    from assurex_claim_engine import notifications

    monkeypatch.setattr(
        notifications,
        "SessionLocal",
        lambda: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    assert notifications.notify_user("USR-0001", "x", "Title", "Message") is False


def test_missing_documents_notification(client, customer_headers, models_ready):
    product_id = _product(client, customer_headers)
    claim = _submit(client, customer_headers, product_id)
    assert claim.status_code == 201, claim.content
    claim_id = claim.json()["claim_id"]

    items = client.get("/api/v1/notifications?per_page=100", **customer_headers).json()["items"]
    types = {row["type"] for row in items if row["claim_id"] == claim_id}
    assert "missing_documents" in types
