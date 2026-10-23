"""End-to-end tests for the Django Ninja REST API."""

from __future__ import annotations

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client


def _login(client: Client, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return response.json()["access_token"]

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

PRODUCT_PAYLOAD = {
    "product_name": "Test Ultrabook",
    "category": "electronics",
    "brand": "TestBrand",
    "model_number": "TB-1000",
    "serial_number": "SN-API-0001",
    "purchase_date": "2025-06-01",
    "purchase_price": 1200.0,
    "retailer": "Test Retailer",
    "warranty_duration_months": 24,
}


# --------------------------------------------------------------------------- #
# Public endpoints
# --------------------------------------------------------------------------- #
def test_health_is_public(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "assurex-claim-engine-rest-api"
    assert "models_ready" in body


def test_api_root_and_openapi(client):
    root = client.get("/api/")
    assert root.status_code == 200
    assert root.json()["docs"] == "/api/docs"

    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    payload = schema.json()
    assert payload["info"]["title"] == "AssureX Claim Engine API"
    assert "/api/v1/claims" in payload["paths"]


def test_login_rejects_bad_password(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"email": "customer@assurex.com", "password": "wrong-password"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_protected_route_requires_auth(client):
    assert client.get("/api/v1/claims").status_code == 401


# --------------------------------------------------------------------------- #
# Authentication / profile
# --------------------------------------------------------------------------- #
def test_me_returns_principal(client, customer_headers):
    response = client.get("/api/v1/auth/me", **customer_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["user_id"] == "USR-0001"
    assert body["user"]["role"] == "customer"
    assert "products" in body["stats"]


def test_register_and_login_roundtrip(client):
    payload = {
        "full_name": "API Tester",
        "email": "api.tester@example.com",
        "password": "verysecret123",
        "role": "reviewer",  # must be downgraded to customer
    }
    created = client.post(
        "/api/v1/auth/register", data=payload, content_type="application/json"
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["user"]["role"] == "customer"
    assert body["access_token"]

    duplicate = client.post(
        "/api/v1/auth/register", data=payload, content_type="application/json"
    )
    assert duplicate.status_code == 400

    me = client.get(
        "/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {body['access_token']}"
    )
    assert me.status_code == 200


def test_update_profile_and_password(client, customer_headers):
    updated = client.patch(
        "/api/v1/auth/me",
        data=json.dumps(
            {
                "full_name": "John Customer",
                "email": "customer@assurex.com",
                "phone_number": "+92-300-0000000",
                "mailing_address": "Karachi",
            }
        ),
        content_type="application/json",
        **customer_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["phone_number"] == "+92-300-0000000"

    changed = client.post(
        "/api/v1/auth/change-password",
        data=json.dumps(
            {"current_password": "customer123", "new_password": "customer12345"}
        ),
        content_type="application/json",
        **customer_headers,
    )
    assert changed.status_code == 200

    # Restore the seeded password for other tests.
    login = client.post(
        "/api/v1/auth/login",
        data={"email": "customer@assurex.com", "password": "customer12345"},
        content_type="application/json",
    )
    token = login.json()["access_token"]
    client.post(
        "/api/v1/auth/change-password",
        data=json.dumps(
            {"current_password": "customer12345", "new_password": "customer123"}
        ),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


# --------------------------------------------------------------------------- #
# Products / warranties
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def product_id():
    client = Client()
    token = _login(client, "customer@assurex.com", "customer123")
    response = client.post(
        "/api/v1/products",
        data=json.dumps(PRODUCT_PAYLOAD),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201, response.content
    return response.json()["product"]["product_id"]


def test_product_creation_and_listing(client, customer_headers, product_id):
    detail = client.get(f"/api/v1/products/{product_id}", **customer_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["product"]["serial_number"] == "SN-API-0001"
    assert body["warranty_status"] in {
        "Active",
        "Expiring Soon",
        "Grace Period Active",
        "Expired",
        "Unknown",
    }

    listing = client.get("/api/v1/products?category=electronics", **customer_headers)
    assert listing.status_code == 200
    ids = [row["product"]["product_id"] for row in listing.json()["items"]]
    assert product_id in ids


def test_warranties_and_alerts(client, customer_headers, product_id):
    warranties = client.get("/api/v1/warranties", **customer_headers)
    assert warranties.status_code == 200

    detail = client.get(f"/api/v1/warranties/{product_id}", **customer_headers)
    assert detail.status_code == 200
    assert detail.json()["product"]["product_id"] == product_id

    alerts = client.get("/api/v1/alerts?tab=all", **customer_headers)
    assert alerts.status_code == 200
    assert "summary" in alerts.json()


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
def test_document_upload_duplicate_and_delete(client, customer_headers, product_id):
    upload = SimpleUploadedFile("receipt.png", PNG_BYTES, content_type="image/png")
    created = client.post(
        "/api/v1/documents",
        data={"file_type": "purchase_receipt", "product_id": product_id, "upload": upload},
        **customer_headers,
    )
    assert created.status_code == 201, created.content
    doc = created.json()
    doc_id = doc["doc_id"]
    assert doc["file_hash"]

    duplicate = client.post(
        "/api/v1/documents",
        data={
            "file_type": "purchase_receipt",
            "product_id": product_id,
            "upload": SimpleUploadedFile("receipt-copy.png", PNG_BYTES, content_type="image/png"),
        },
        **customer_headers,
    )
    assert duplicate.status_code == 201
    assert doc_id in duplicate.json()["duplicate_of"]

    downloaded = client.get(f"/api/v1/documents/{doc_id}/download", **customer_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_BYTES

    deleted = client.delete(f"/api/v1/documents/{doc_id}", **customer_headers)
    assert deleted.status_code == 200

    missing = client.get(f"/api/v1/documents/{doc_id}", **customer_headers)
    assert missing.status_code == 404


# --------------------------------------------------------------------------- #
# Claims (model dependent)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def submitted_claim(product_id, models_ready):
    client = Client()
    token = _login(client, "customer@assurex.com", "customer123")
    response = client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "fault_category": "motherboard_failure",
            "damage_type": "none",
            "fault_occurrence_date": "2026-09-01",
            "claim_submission_date": "2026-10-01",
            "description": "API integration test claim.",
            "action_type": "submit",
            "receipt_file": SimpleUploadedFile("receipt.png", PNG_BYTES, content_type="image/png"),
        },
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_claim_submission_runs_dual_models(client, customer_headers, submitted_claim):
    claim = submitted_claim
    assert claim["claim_id"].startswith("CLM-")
    assert claim["final_decision"] in {
        "Likely Valid",
        "Likely Invalid",
        "Manual Review Required",
    }
    assert claim["python_predicted_class"]
    assert claim["vision_predicted_class"]
    assert claim["dossier"]["comparison"]["consistency_status"]
    assert claim["status"] in {"Approved", "Rejected", "Manual Review"}


def test_claim_list_and_detail(client, customer_headers, submitted_claim):
    listing = client.get("/api/v1/claims?status=", **customer_headers)
    assert listing.status_code == 200
    ids = [item["claim_id"] for item in listing.json()["items"]]
    assert submitted_claim["claim_id"] in ids

    detail = client.get(
        f"/api/v1/claims/{submitted_claim['claim_id']}", **customer_headers
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["narrative_summary"]
    assert body["summary_card_url"].endswith("/summary-card")


def test_claim_summary_card_and_reports(client, customer_headers, submitted_claim):
    claim_id = submitted_claim["claim_id"]

    card = client.get(f"/api/v1/claims/{claim_id}/summary-card", **customer_headers)
    assert card.status_code == 200
    assert card["Content-Type"] == "image/png"
    assert card.content.startswith(b"\x89PNG")

    pdf = client.get(f"/api/v1/claims/{claim_id}/report.pdf", **customer_headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")

    markdown = client.get(f"/api/v1/claims/{claim_id}/report.md", **customer_headers)
    assert markdown.status_code == 200
    assert claim_id.encode() in markdown.content


def test_draft_claim_creation(client, customer_headers, product_id):
    response = client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "fault_category": "screen_flicker_defect",
            "fault_occurrence_date": "2026-09-15",
            "action_type": "draft",
            "description": "Draft from REST API.",
        },
        **customer_headers,
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "Draft"
    assert body["final_decision"] == "Draft"


def test_precheck(client, customer_headers, product_id):
    response = client.post(
        "/api/v1/claims/precheck",
        data=json.dumps(
            {
                "product_id": product_id,
                "fault_occurrence_date": "2026-09-01",
                "claim_submission_date": "2026-10-01",
                "fault_category": "motherboard_failure",
                "damage_type": "none",
            }
        ),
        content_type="application/json",
        **customer_headers,
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert "ready" in body
    assert "missing_documents" in body


# --------------------------------------------------------------------------- #
# Reviewer and admin RBAC
# --------------------------------------------------------------------------- #
def test_customer_cannot_access_admin(client, customer_headers):
    assert client.get("/api/v1/admin/analytics", **customer_headers).status_code == 403
    assert client.get("/api/v1/review/queue", **customer_headers).status_code == 403


def test_reviewer_queue_and_override(client, reviewer_headers, submitted_claim):
    queue = client.get("/api/v1/review/queue", **reviewer_headers)
    assert queue.status_code == 200

    decision = client.post(
        f"/api/v1/review/{submitted_claim['claim_id']}/decision",
        data=json.dumps(
            {
                "action": "Approved",
                "comments": "Evidence verified by API test reviewer.",
            }
        ),
        content_type="application/json",
        **reviewer_headers,
    )
    assert decision.status_code == 200, decision.content
    body = decision.json()
    assert body["status"] == "Approved"
    assert body["override_flag"] is True


def test_admin_endpoints(client, admin_headers, submitted_claim):
    analytics = client.get("/api/v1/admin/analytics", **admin_headers)
    assert analytics.status_code == 200
    assert analytics.json()["totals"]["claims"] >= 1

    policies = client.get("/api/v1/admin/policies", **admin_headers)
    assert policies.status_code == 200
    assert "electronics" in policies.json()["policies"]

    single = client.get("/api/v1/admin/policies/electronics", **admin_headers)
    assert single.status_code == 200
    assert single.json()["policy"]["product_category"] == "electronics"

    logs = client.get("/api/v1/admin/audit-logs?action=AI", **admin_headers)
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1

    export = client.get("/api/v1/admin/export/claims.csv", **admin_headers)
    assert export.status_code == 200
    assert submitted_claim["claim_id"] in export.content.decode()

    monitoring = client.get("/api/v1/admin/monitoring", **admin_headers)
    assert monitoring.status_code == 200
    assert "flags" in monitoring.json()

    settings_response = client.get("/api/v1/admin/settings", **admin_headers)
    assert settings_response.status_code == 200
    assert "model_version" in settings_response.json()["settings"]


def test_csv_import(client, customer_headers, models_ready):
    csv_body = (
        "claim_id,product_name,serial_number,purchase_date,fault_category,"
        "fault_occurrence_date,claim_submission_date,damage_type\n"
        "CLM-CSV-0001,CSV Laptop,SN-CSV-1,2025-05-01,motherboard_failure,"
        "2026-08-01,2026-10-01,none\n"
    )
    response = client.post(
        "/api/v1/claims/import-csv",
        data={"upload": SimpleUploadedFile("claims.csv", csv_body.encode(), content_type="text/csv")},
        **customer_headers,
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["imported_count"] == 1
    assert body["errors"] == []
