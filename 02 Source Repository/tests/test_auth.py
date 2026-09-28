"""
AssureX Claim Engine - Authentication & RBAC Verification Tests
Tests login, registration, session management, and role-based route access controls.
"""

import pytest
from fastapi.testclient import TestClient
from assurex_claim_engine.web.app import app
from assurex_claim_engine.db.database import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)

def test_01_unauthenticated_access_redirects_to_login(client):
    """Unauthenticated request to protected admin route should redirect to /login."""
    response = client.get("/admin/analytics")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_02_login_invalid_credentials(client):
    """Invalid email or password should re-render login page with error."""
    response = client.post("/login", data={"email": "wrong@assurex.com", "password": "wrongpassword"})
    assert response.status_code == 400
    assert "Invalid email or password" in response.text

def test_03_admin_login_and_analytics_access(client):
    """Admin user login sets session and grants access to /admin/analytics."""
    login_resp = client.post("/login", data={"email": "admin@assurex.com", "password": "admin123"})
    assert login_resp.status_code == 303
    assert login_resp.headers["location"] == "/"

    analytics_resp = client.get("/admin/analytics")
    assert analytics_resp.status_code == 200
    assert "System Analytics" in analytics_resp.text

def test_04_customer_role_restriction(client):
    """Customer user login grants dashboard access but returns 403 on admin analytics."""
    login_resp = client.post("/login", data={"email": "customer@assurex.com", "password": "customer123"})
    assert login_resp.status_code == 303

    # Can access home/dashboard
    home_resp = client.get("/")
    assert home_resp.status_code == 200

    # Cannot access admin analytics (403 Forbidden)
    analytics_resp = client.get("/admin/analytics")
    assert analytics_resp.status_code == 403
    assert "Access Denied" in analytics_resp.text

def test_05_reviewer_role_access(client):
    """Reviewer user can access /reviewer/queue but gets 403 on admin analytics."""
    login_resp = client.post("/login", data={"email": "reviewer@assurex.com", "password": "reviewer123"})
    assert login_resp.status_code == 303

    queue_resp = client.get("/reviewer/queue")
    assert queue_resp.status_code == 200

    analytics_resp = client.get("/admin/analytics")
    assert analytics_resp.status_code == 403

def test_06_new_user_registration(client):
    """Registering a new customer creates user account, sets session, and logs in."""
    import uuid
    email = f"test_{uuid.uuid4().hex[:6]}@assurex.com"
    reg_resp = client.post("/register", data={
        "full_name": "Test New Customer",
        "email": email,
        "password": "testpassword123",
        "role": "customer"
    })
    assert reg_resp.status_code == 303

    home_resp = client.get("/")
    assert home_resp.status_code == 200
    assert "Test New Customer" in home_resp.text

def test_07_logout_clears_session(client):
    """Logout clears session cookies and redirects to /login."""
    client.post("/login", data={"email": "admin@assurex.com", "password": "admin123"})
    
    logout_resp = client.get("/logout")
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login"

    protected_resp = client.get("/admin/analytics")
    assert protected_resp.status_code == 303
    assert protected_resp.headers["location"] == "/login"
