"""Role-enforcement tests for the REST API (server-side, not UI)."""

from __future__ import annotations

import json
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from assurex_claim_engine.db.database import AuditLog, SessionLocal

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

ROLE_CREDENTIALS = {
    "customer": ("customer@assurex.com", "customer123"),
    "service_center": ("service@assurex.com", "service123"),
    "reviewer": ("reviewer@assurex.com", "reviewer123"),
    "admin": ("admin@assurex.com", "admin123"),
}
CREATE_CASES = [
    ("customer", 201),
    ("service_center", 201),
    ("reviewer", 403),
    ("admin", 201),
]


def _login(client: Client, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def headers(client: Client) -> dict[str, dict]:
    return {role: _login(client, *creds) for role, creds in ROLE_CREDENTIALS.items()}


def _product_payload(serial: str | None = None) -> dict:
    return {
        "product_name": "Role Test Laptop",
        "category": "electronics",
        "brand": "RoleBrand",
        "model_number": "RT-1",
        "serial_number": serial or f"ROLE-{uuid.uuid4().hex[:10]}",
        "purchase_date": "2025-06-01",
        "purchase_price": 1000.0,
        "retailer": "Role Retailer",
        "warranty_duration_months": 24,
    }


def _create_product(client: Client, role_headers: dict, serial: str | None = None):
    return client.post(
        "/api/v1/products",
        data=json.dumps(_product_payload(serial)),
        content_type="application/json",
        **role_headers,
    )


def _upload_document(client: Client, role_headers: dict, product_id: str):
    return client.post(
        "/api/v1/documents",
        data={
            "file_type": "purchase_receipt",
            "product_id": product_id,
            "upload": SimpleUploadedFile("receipt.png", PNG_BYTES, content_type="image/png"),
        },
        **role_headers,
    )


def _draft_claim(client: Client, role_headers: dict, product_id: str):
    return client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "fault_category": "motherboard_failure",
            "damage_type": "none",
            "fault_occurrence_date": "2026-10-01",
            "claim_submission_date": "2026-10-23",
            "description": "Role enforcement draft",
            "action_type": "draft",
        },
        **role_headers,
    )


def _repair(client: Client, role_headers: dict, product_id: str):
    return client.post(
        "/api/v1/repairs",
        data=json.dumps(
            {
                "product_id": product_id,
                "repair_date": "2026-05-01",
                "service_center_name": "Role Test Center",
                "replaced_parts": "Motherboard",
                "repair_cost": 100,
                "outcome": "Completed",
                "authorized": True,
            }
        ),
        content_type="application/json",
        **role_headers,
    )


@pytest.fixture()
def seed_product(client: Client, headers) -> str:
    response = _create_product(client, headers["customer"])
    assert response.status_code == 201, response.content
    return response.json()["product"]["product_id"]


# --------------------------------------------------------------------------- #
# Intake routes: customer + service_center + admin pass, reviewer 403
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("role,expected", CREATE_CASES)
def test_create_product_per_role(client, headers, role, expected):
    response = _create_product(client, headers[role])
    assert response.status_code == expected, response.content


@pytest.mark.parametrize("role,expected", CREATE_CASES)
def test_create_claim_per_role(client, headers, seed_product, role, expected):
    if role == "reviewer":
        product_id = seed_product
    else:
        created = _create_product(client, headers[role])
        assert created.status_code == 201, created.content
        product_id = created.json()["product"]["product_id"]
    response = _draft_claim(client, headers[role], product_id)
    assert response.status_code == expected, response.content


@pytest.mark.parametrize("role,expected", CREATE_CASES)
def test_upload_document_per_role(client, headers, seed_product, role, expected):
    if role == "reviewer":
        product_id = seed_product
    else:
        created = _create_product(client, headers[role])
        assert created.status_code == 201, created.content
        product_id = created.json()["product"]["product_id"]
    response = _upload_document(client, headers[role], product_id)
    assert response.status_code == expected, response.content


@pytest.mark.parametrize("role,expected", CREATE_CASES)
def test_create_repair_per_role(client, headers, seed_product, role, expected):
    if role == "reviewer":
        product_id = seed_product
    else:
        created = _create_product(client, headers[role])
        assert created.status_code == 201, created.content
        product_id = created.json()["product"]["product_id"]
    response = _repair(client, headers[role], product_id)
    assert response.status_code == expected, response.content


# --------------------------------------------------------------------------- #
# Document mutations: owner or admin only; reviewer read-only
# --------------------------------------------------------------------------- #
@pytest.fixture()
def owner_document(client, headers) -> tuple[dict, str, str]:
    product = _create_product(client, headers["customer"])
    assert product.status_code == 201
    product_id = product.json()["product"]["product_id"]
    uploaded = _upload_document(client, headers["customer"], product_id)
    assert uploaded.status_code == 201, uploaded.content
    return headers["customer"], product_id, uploaded.json()["doc_id"]


def _other_customer(client: Client, headers) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        data=json.dumps(
            {
                "full_name": "Other Customer",
                "email": f"other.{uuid.uuid4().hex[:8]}@example.com",
                "password": "verysecret123",
                "role": "customer",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201, response.content
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


def _replace_document(client: Client, role_headers: dict, doc_id: str):
    return client.post(
        f"/api/v1/documents/{doc_id}/replace",
        data={
            "file_type": "purchase_receipt",
            "upload": SimpleUploadedFile("replacement.png", PNG_BYTES, content_type="image/png"),
        },
        **role_headers,
    )


def _verify_document(client: Client, role_headers: dict, doc_id: str):
    return client.post(
        f"/api/v1/documents/{doc_id}/verify",
        data=json.dumps(
            {
                "purchase_date": "2025-06-01",
                "invoice_number": "INV-ROLE-1",
                "product_name": "Role Test Laptop",
                "model_number": "RT-1",
                "serial_number": "SN-ROLE-1",
                "retailer_name": "Role Retailer",
                "purchase_amount": "1000",
                "warranty_period": "24 months",
            }
        ),
        content_type="application/json",
        **role_headers,
    )


def test_reviewer_cannot_mutate_evidence(client, headers, owner_document):
    _, _, doc_id = owner_document
    assert client.delete(f"/api/v1/documents/{doc_id}", **headers["reviewer"]).status_code == 403
    assert _replace_document(client, headers["reviewer"], doc_id).status_code == 403
    assert _verify_document(client, headers["reviewer"], doc_id).status_code == 403


def test_service_center_cannot_mutate_other_customers_document(client, headers, owner_document):
    _, _, doc_id = owner_document
    assert client.delete(f"/api/v1/documents/{doc_id}", **headers["service_center"]).status_code == 403
    assert _replace_document(client, headers["service_center"], doc_id).status_code == 403
    assert _verify_document(client, headers["service_center"], doc_id).status_code == 403


def test_customer_cannot_mutate_another_customers_document(client, headers, owner_document):
    _, _, doc_id = owner_document
    other = _other_customer(client, headers)
    assert client.delete(f"/api/v1/documents/{doc_id}", **other).status_code == 403
    assert _replace_document(client, other, doc_id).status_code == 403
    assert _verify_document(client, other, doc_id).status_code == 403


def test_admin_can_mutate_any_document_and_audit_is_written(client, headers, owner_document):
    _, _, doc_id = owner_document

    verified = _verify_document(client, headers["admin"], doc_id)
    assert verified.status_code == 200, verified.content

    replaced = _replace_document(client, headers["admin"], doc_id)
    assert replaced.status_code == 200, replaced.content

    deleted = client.delete(f"/api/v1/documents/{doc_id}", **headers["admin"])
    assert deleted.status_code == 200, deleted.content

    with SessionLocal() as db:
        actions = [
            row.action
            for row in db.query(AuditLog).filter(AuditLog.entity_id == doc_id).all()
        ]
    assert "Document Replace" in actions
    assert "Document Delete" in actions


def test_owner_can_verify_and_delete_own_document(client, headers):
    product = _create_product(client, headers["customer"])
    product_id = product.json()["product"]["product_id"]
    uploaded = _upload_document(client, headers["customer"], product_id)
    doc_id = uploaded.json()["doc_id"]
    assert _verify_document(client, headers["customer"], doc_id).status_code == 200
    assert client.delete(f"/api/v1/documents/{doc_id}", **headers["customer"]).status_code == 200


def test_service_center_owner_can_verify_own_document(client, headers):
    product = _create_product(client, headers["service_center"])
    product_id = product.json()["product"]["product_id"]
    uploaded = _upload_document(client, headers["service_center"], product_id)
    doc_id = uploaded.json()["doc_id"]
    assert _verify_document(client, headers["service_center"], doc_id).status_code == 200


# --------------------------------------------------------------------------- #
# Reviewer remains read-only but keeps review access
# --------------------------------------------------------------------------- #
def test_reviewer_can_read_documents_and_use_review_queue(client, headers, owner_document):
    _, _, doc_id = owner_document
    assert client.get(f"/api/v1/documents/{doc_id}", **headers["reviewer"]).status_code == 200
    assert client.get(f"/api/v1/documents/{doc_id}/download", **headers["reviewer"]).status_code == 200
    assert client.get("/api/v1/review/queue", **headers["reviewer"]).status_code == 200


def test_admin_can_create_all_intake_records(client, headers):
    product = _create_product(client, headers["admin"])
    assert product.status_code == 201
    product_id = product.json()["product"]["product_id"]
    assert _upload_document(client, headers["admin"], product_id).status_code == 201
    assert _draft_claim(client, headers["admin"], product_id).status_code == 201
    assert _repair(client, headers["admin"], product_id).status_code == 201
