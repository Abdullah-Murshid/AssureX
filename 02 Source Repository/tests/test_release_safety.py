import hashlib
from fastapi.testclient import TestClient
from assurex_claim_engine.db.database import hash_password,verify_password,init_db
from assurex_claim_engine.web.app import app

def test_password_salted_and_legacy_verification():
    a=hash_password('demo123');b=hash_password('demo123')
    assert a!=b and verify_password('demo123',a)
    assert not verify_password('incorrect',a)
    assert verify_password('demo123',hashlib.sha256(b'demo123').hexdigest())

def test_upload_requires_login():
    init_db()
    with TestClient(app,follow_redirects=False) as c:
        assert c.get('/uploads/unknown.png').status_code==303

def test_registration_cannot_create_admin():
    init_db()
    c=TestClient(app,follow_redirects=False)
    response=c.post('/register',data={'full_name':'Synthetic privilege test','email':'privilege-test@example.test','password':'demo123','role':'admin'})
    assert response.status_code in (303,400)
    assert c.get('/admin/analytics').status_code in (303,403)
