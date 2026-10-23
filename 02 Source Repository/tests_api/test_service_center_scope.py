"""Least-privilege scope for service-centre users."""

from __future__ import annotations

import json
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

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
    assert response.status_code == 200, response.content
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def service_headers(client):
    return _login(client, "service@assurex.com", "service123")


def _product(client, headers, *, name="Scope Laptop", purchase="2025-06-01", months=24):
    response = client.post(
        "/api/v1/products",
        data=json.dumps(
            {
                "product_name": name,
                "category": "electronics",
                "brand": "ScopeBrand",
                "model_number": "S-1",
                "serial_number": f"S-{uuid.uuid4().hex[:10]}",
                "purchase_date": purchase,
                "purchase_price": 1000.0,
                "retailer": "Scope Retailer",
                "warranty_duration_months": months,
            }
        ),
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 201, response.content
    return response.json()["product"]["product_id"]


def _document(client, headers, product_id):
    response = client.post(
        "/api/v1/documents",
        data={
            "file_type": "purchase_receipt",
            "product_id": product_id,
            "upload": SimpleUploadedFile("receipt.png", PNG_BYTES, content_type="image/png"),
        },
        **headers,
    )
    assert response.status_code == 201, response.content
    return response.json()["doc_id"]


def _claim(client, headers, product_id):
    response = client.post(
        "/api/v1/claims",
        data={
            "product_id": product_id,
            "fault_category": "motherboard_failure",
            "damage_type": "none",
            "fault_occurrence_date": "2026-10-01",
            "claim_submission_date": "2026-10-23",
            "description": "Scope draft",
            "action_type": "draft",
        },
        **headers,
    )
    assert response.status_code == 201, response.content
    return response.json()["claim_id"]


def _repair(client, headers, product_id):
    return client.post(
        "/api/v1/repairs",
        data=json.dumps(
            {
                "product_id": product_id,
                "repair_date": "2026-05-01",
                "service_center_name": "Scope Centre",
                "replaced_parts": "Board",
                "repair_cost": 50,
                "outcome": "Completed",
                "authorized": True,
            }
        ),
        content_type="application/json",
        **headers,
    )


@pytest.fixture()
def records(client, customer_headers, service_headers):
    customer_product = _product(client, customer_headers, name="Customer Owned")
    customer_doc = _document(client, customer_headers, customer_product)
    customer_claim = _claim(client, customer_headers, customer_product)

    service_product = _product(client, service_headers, name="Service Owned")
    service_doc = _document(client, service_headers, service_product)
    service_claim = _claim(client, service_headers, service_product)
    assert _repair(client, service_headers, service_product).status_code == 201
    customer_repair = _repair(client, customer_headers, customer_product)
    assert customer_repair.status_code == 201

    return {
        "customer_product": customer_product,
        "customer_doc": customer_doc,
        "customer_claim": customer_claim,
        "service_product": service_product,
        "service_doc": service_doc,
        "service_claim": service_claim,
        "customer_repair": customer_repair.json()["repair_id"],
    }


def _ids(payload, key):
    return {item[key] for item in payload["items"]}


def test_service_center_lists_only_own_records(client, service_headers, records):
    products = client.get("/api/v1/products?per_page=100", **service_headers).json()
    claims = client.get("/api/v1/claims?per_page=100", **service_headers).json()
    documents = client.get("/api/v1/documents?per_page=100", **service_headers).json()
    repairs = client.get("/api/v1/repairs?per_page=100", **service_headers).json()

    assert records["service_product"] in {row["product"]["product_id"] for row in products["items"]}
    assert records["customer_product"] not in {row["product"]["product_id"] for row in products["items"]}
    assert records["service_claim"] in _ids(claims, "claim_id")
    assert records["customer_claim"] not in _ids(claims, "claim_id")
    assert records["service_doc"] in _ids(documents, "doc_id")
    assert records["customer_doc"] not in _ids(documents, "doc_id")
    repair_ids = {row["repair_id"] for row in repairs["items"]}
    assert records["customer_repair"] not in repair_ids


def test_service_center_cannot_read_other_users_records(client, service_headers, records):
    customer_product = records["customer_product"]
    customer_claim = records["customer_claim"]
    customer_doc = records["customer_doc"]

    assert client.get(f"/api/v1/products/{customer_product}", **service_headers).status_code == 403
    assert client.get(f"/api/v1/claims/{customer_claim}", **service_headers).status_code == 403
    assert client.get(f"/api/v1/claims/{customer_claim}/history", **service_headers).status_code == 403
    assert client.get(f"/api/v1/claims/{customer_claim}/report.pdf", **service_headers).status_code == 403
    assert client.get(f"/api/v1/documents/{customer_doc}/download", **service_headers).status_code == 404
    assert client.delete(f"/api/v1/documents/{customer_doc}", **service_headers).status_code == 403
    assert client.post(
        f"/api/v1/claims/{records['service_claim']}/documents/{customer_doc}",
        **service_headers,
    ).status_code == 403


def test_service_center_can_use_own_records(client, service_headers, records):
    product_id = records["service_product"]
    claim_id = records["service_claim"]
    doc_id = records["service_doc"]

    assert client.get(f"/api/v1/products/{product_id}", **service_headers).status_code == 200
    assert client.get(f"/api/v1/claims/{claim_id}", **service_headers).status_code == 200
    assert client.get(f"/api/v1/claims/{claim_id}/history", **service_headers).status_code == 200
    assert client.get(f"/api/v1/claims/{claim_id}/report.pdf", **service_headers).status_code == 200
    assert client.get(f"/api/v1/documents/{doc_id}/download", **service_headers).status_code == 200
    assert client.delete(f"/api/v1/documents/{doc_id}", **service_headers).status_code == 200


def test_customer_behavior_is_unchanged(client, customer_headers, records):
    assert client.get(
        f"/api/v1/products/{records['customer_product']}", **customer_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/claims/{records['customer_claim']}", **customer_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/products/{records['service_product']}", **customer_headers
    ).status_code == 403
    assert client.get(
        f"/api/v1/claims/{records['service_claim']}", **customer_headers
    ).status_code == 403


def test_reviewer_and_admin_still_see_everything(client, reviewer_headers, admin_headers, records):
    for headers in (reviewer_headers, admin_headers):
        products = client.get("/api/v1/products?per_page=100", **headers).json()
        product_ids = {row["product"]["product_id"] for row in products["items"]}
        assert records["customer_product"] in product_ids
        assert records["service_product"] in product_ids
        assert client.get(
            f"/api/v1/claims/{records['customer_claim']}", **headers
        ).status_code == 200
        assert client.get(
            f"/api/v1/documents/{records['customer_doc']}/download", **headers
        ).status_code == 200


def test_reviewer_cannot_precheck_or_attach(client, reviewer_headers, records):
    precheck = client.post(
        "/api/v1/claims/precheck",
        data=json.dumps({"product_id": records["customer_product"], "fault_occurrence_date": "2026-10-01", "claim_submission_date": "2026-10-23"}),
        content_type="application/json",
        **reviewer_headers,
    )
    assert precheck.status_code == 403, precheck.content
    attach = client.post(
        f"/api/v1/claims/{records['customer_claim']}/documents/{records['customer_doc']}",
        **reviewer_headers,
    )
    assert attach.status_code == 403, attach.content


def test_service_center_dashboard_and_alerts_are_scoped(client, service_headers, customer_headers, records):
    me = client.get("/api/v1/auth/me", **service_headers).json()
    products = client.get("/api/v1/products?per_page=100", **service_headers).json()
    claims = client.get("/api/v1/claims?per_page=100", **service_headers).json()
    assert me["stats"]["products"] == products["total"]
    assert me["stats"]["claims"] == claims["total"]

    service_expiring = _product(
        client, service_headers, name="Service Expiring", purchase="2024-11-15"
    )
    customer_expiring = _product(
        client, customer_headers, name="Customer Expiring", purchase="2024-11-15"
    )
    alerts = client.get("/api/v1/alerts?tab=all&per_page=100", **service_headers).json()
    alert_product_ids = {row["product"]["product_id"] for row in alerts["alerts"]}
    assert service_expiring in alert_product_ids
    assert customer_expiring not in alert_product_ids
