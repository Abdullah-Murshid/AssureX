"""End-to-end smoke test for the AssureX REST API.

Usage:
    uv run python smoke_rest_api.py                 # http://127.0.0.1:8011
    uv run python smoke_rest_api.py --base-url http://127.0.0.1:8011

The script exercises the public health/docs endpoints, customer authentication,
product registration, pre-check, evidence upload, full dual-model claim
adjudication, the summary card + PDF report, reviewer override, and admin
analytics/export. It prints PASS/FAIL per step and exits non-zero on failure.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date

import httpx

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name} {detail}")


def api(base: str) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=120.0)


def login(client: httpx.Client, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with api(base) as client:
        # ---------------------------------------------------------------- #
        # Public surface
        # ---------------------------------------------------------------- #
        root = client.get("/api/")
        check("GET /api/", root.status_code == 200, root.json().get("service", ""))

        health = client.get("/api/v1/health")
        body = health.json()
        check(
            "GET /api/v1/health",
            health.status_code == 200 and body.get("models_ready") is True,
            f"python={body.get('python_model_ready')} gtm={body.get('gtm_model_ready')} "
            f"load={body.get('load_seconds')}s",
        )

        docs = client.get("/api/docs")
        check("GET /api/docs", docs.status_code == 200, f"{len(docs.content)} bytes")

        schema = client.get("/api/openapi.json").json()
        check("GET /api/openapi.json", len(schema.get("paths", {})) >= 30,
              f"{len(schema.get('paths', {}))} paths")

        # ---------------------------------------------------------------- #
        # Customer flow
        # ---------------------------------------------------------------- #
        headers = login(client, "customer@assurex.com", "customer123")
        me = client.get("/api/v1/auth/me", headers=headers)
        check("customer login + /auth/me", me.status_code == 200, me.json()["user"]["user_id"])

        serial = f"SMOKE-{int(time.time())}"
        product = client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "product_name": "Smoke Test Laptop",
                "category": "electronics",
                "brand": "SmokeBrand",
                "model_number": "SMK-1",
                "serial_number": serial,
                "purchase_date": "2025-06-01",
                "purchase_price": 1500,
                "retailer": "Smoke Retailer",
                "warranty_duration_months": 24,
            },
        )
        check("POST /products", product.status_code == 201, product.text[:120])
        product_id = product.json()["product"]["product_id"]

        precheck = client.post(
            "/api/v1/claims/precheck",
            headers=headers,
            json={
                "product_id": product_id,
                "fault_occurrence_date": "2026-09-01",
                "claim_submission_date": date.today().isoformat(),
                "fault_category": "motherboard_failure",
                "damage_type": "none",
            },
        )
        check("POST /claims/precheck", precheck.status_code == 200, str(precheck.json().get("ready")))

        document = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"file_type": "purchase_receipt", "product_id": product_id},
            files={"upload": ("receipt.png", PNG_1X1, "image/png")},
        )
        check("POST /documents", document.status_code == 201, document.json().get("doc_id", ""))
        doc_id = document.json()["doc_id"]

        claim_response = client.post(
            "/api/v1/claims",
            headers=headers,
            data={
                "product_id": product_id,
                "fault_category": "motherboard_failure",
                "damage_type": "none",
                "fault_occurrence_date": "2026-09-01",
                "claim_submission_date": date.today().isoformat(),
                "description": "Smoke-test claim submitted by smoke_rest_api.py",
                "attach_doc_ids": doc_id,
                "action_type": "submit",
            },
            files={"receipt_file": ("receipt.png", PNG_1X1, "image/png")},
        )
        check("POST /claims (dual-model)", claim_response.status_code == 201, claim_response.text[:160])
        if claim_response.status_code != 201:
            return 1
        claim = claim_response.json()
        claim_id = claim["claim_id"]
        check(
            "claim decision",
            claim["final_decision"] in {"Likely Valid", "Likely Invalid", "Manual Review Required"},
            f"{claim['final_decision']} / python={claim['python_predicted_class']} "
            f"gtm={claim['vision_predicted_class']} / {claim['consistency_status']}",
        )

        detail = client.get(f"/api/v1/claims/{claim_id}", headers=headers)
        check("GET /claims/{id}", detail.status_code == 200 and bool(detail.json().get("narrative_summary")))

        card = client.get(f"/api/v1/claims/{claim_id}/summary-card", headers=headers)
        check("GET summary-card", card.status_code == 200 and card.content[:4] == b"\x89PNG",
              f"{len(card.content)} bytes")

        pdf = client.get(f"/api/v1/claims/{claim_id}/report.pdf", headers=headers)
        check("GET report.pdf", pdf.status_code == 200 and pdf.content[:4] == b"%PDF",
              f"{len(pdf.content)} bytes")

        markdown = client.get(f"/api/v1/claims/{claim_id}/report.md", headers=headers)
        check("GET report.md", markdown.status_code == 200 and claim_id.encode() in markdown.content)

        forbidden = client.get("/api/v1/admin/analytics", headers=headers)
        check("RBAC: customer blocked from admin", forbidden.status_code == 403)

        # ---------------------------------------------------------------- #
        # Reviewer flow
        # ---------------------------------------------------------------- #
        reviewer = login(client, "reviewer@assurex.com", "reviewer123")
        queue = client.get("/api/v1/review/queue", headers=reviewer)
        check("reviewer queue", queue.status_code == 200, f"{queue.json()['total']} item(s)")

        override = client.post(
            f"/api/v1/review/{claim_id}/decision",
            headers=reviewer,
            json={"action": "Approved", "comments": "Smoke test reviewer approval."},
        )
        check("reviewer override", override.status_code == 200 and override.json()["override_flag"] is True,
              override.json().get("status", ""))

        # ---------------------------------------------------------------- #
        # Admin flow
        # ---------------------------------------------------------------- #
        admin = login(client, "admin@assurex.com", "admin123")
        analytics = client.get("/api/v1/admin/analytics", headers=admin)
        check("admin analytics", analytics.status_code == 200,
              f"{analytics.json()['totals']['claims']} claims")

        policies = client.get("/api/v1/admin/policies/electronics", headers=admin)
        check("admin policy read", policies.status_code == 200)

        export = client.get("/api/v1/admin/export/claims.csv", headers=admin)
        check("admin CSV export", export.status_code == 200 and claim_id.encode() in export.content)

        audit = client.get(f"/api/v1/admin/audit-logs?claim_id={claim_id}", headers=admin)
        check("audit trail", audit.status_code == 200 and audit.json()["total"] >= 3,
              f"{audit.json()['total']} events")

        client.post("/api/v1/auth/logout", headers=headers)

    failed = [name for name, ok, _ in _results if not ok]
    print()
    print(f"{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("Failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
