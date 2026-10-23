"""
AssureX Claim Engine - Web Application Server
FastAPI Web Application providing interactive UI for:
- Session-Based Authentication & Role-Based Access Control (RBAC)
- Claim Intake & File Uploads
- OCR Verification & Extracted Data Edits
- Dual-Model Adjudication Dossier (Python ML vs Vision Summary Card Classifier)
- Manual Reviewer Queue with Override Modal
- Administrator Analytics & Downloadable Reports
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import io
import json
import os
import sys
import time
import threading
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timezone

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, "..", ".."))
_PROJ_DIR = os.path.abspath(os.path.join(_SRC_DIR, ".."))

for _p in [_SRC_DIR, _PROJ_DIR, "."]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import pandas as pd

from assurex_claim_engine.db.database import (
    get_db, init_db, SessionLocal, User, Product, Claim, Document, AuditLog, Repair,
    hash_password, verify_password,
)
from assurex_claim_engine.models.tabular_model import TabularClaimClassifier
from assurex_claim_engine.models.image_classifier import ImageClassifierPipeline
from assurex_claim_engine.decision.fusion import DecisionFusionEngine, generate_narrative_summary
from assurex_claim_engine.decision.derived_features import compute_derived_claim_features
from assurex_claim_engine.decision.contradiction import ContradictionAndDuplicateDetector
from assurex_claim_engine.db.status_history import ensure_initial_status, record_status_transition, record_submission_stages
from assurex_claim_engine import notifications as notification_service
from assurex_claim_engine.rule_engine.evaluator import PolicyRuleEvaluator
from assurex_claim_engine.ocr.parser import DocumentOCRParser
from assurex_claim_engine.web.helpers import (
    scoped_products, scoped_claims, scoped_documents, scoped_repairs,
    next_product_id, next_doc_id, next_repair_id, load_policy, enrich_product,
    warranty_alert_items, warranty_alert_summary, validate_upload, repair_stats_for_product,
    claim_status_steps, documents_by_policy_key, product_to_claim_dict,
    write_audit, find_hash_duplicates, policy_file_map, validate_policy_payload,
    can_access_product, FILE_TYPE_MAP, paginate,
)
from dataset_generator.generate_summary_cards_v6 import render_claim_card_v6 as render_claim_card
from config.settings_loader import get, save_setting
from assurex_claim_engine.reporting.pdf_generator import generate_claim_pdf_report


SECRET_KEY = os.environ.get("SECRET_KEY", "assurex-secret-key-change-in-production-2026")

tabular_classifier = TabularClaimClassifier()
vision_classifier = ImageClassifierPipeline()
fusion_engine = DecisionFusionEngine()
ocr_parser = DocumentOCRParser()

_models_ready = False
_startup_t0 = 0.0


def _load_models_background():
    global _models_ready, _startup_t0
    t0 = time.time()
    _startup_t0 = t0

    t1 = time.time()
    tabular_classifier.load_artifacts()
    print(f"[startup] Tabular model loaded ({time.time()-t1:.2f}s)", flush=True)

    t2 = time.time()
    vision_classifier.load_model()
    print(f"[startup] Vision model loaded ({time.time()-t2:.2f}s)", flush=True)

    _models_ready = tabular_classifier.best_model is not None and vision_classifier.model is not None
    print(f"[startup] All models ready — total {time.time()-t0:.2f}s", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.time()
    init_db()
    print(f"[startup] DB ready ({time.time()-t0:.2f}s) — loading models in background", flush=True)
    thread = threading.Thread(target=_load_models_background, daemon=True, name="model-loader")
    thread.start()
    yield


app = FastAPI(title="AssureX Claim Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False, same_site="lax")

def _resolve_dir(dirname: str) -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "../../../", dirname),
        os.path.join(os.path.dirname(__file__), "../../..", "02. Complete Source Code", dirname),
        dirname,
        os.path.join("02. Complete Source Code", dirname),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return dirname

STATIC_DIR = _resolve_dir("static")
TEMPLATES_DIR = _resolve_dir("templates")
UPLOADS_DIR = _resolve_dir("uploads")
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


templates = Jinja2Templates(directory=TEMPLATES_DIR)
policy_rule_evaluator = PolicyRuleEvaluator()


def _flash(request: Request, message: str, kind: str = "success"):
    request.session["flash"] = message
    request.session["flash_kind"] = kind


def _take_flash(request: Request):
    msg = request.session.pop("flash", None)
    kind = request.session.pop("flash_kind", "success")
    return msg, kind


def render(request: Request, template_name: str, context: dict, status_code: int = 200, db: Session = None):
    user = context.get("user")
    flash, flash_kind = _take_flash(request)
    context.setdefault("flash", flash)
    context.setdefault("flash_kind", flash_kind)
    context.setdefault("alert_count", 0)
    context.setdefault("alert_items", [])
    context.setdefault("status_steps", claim_status_steps())
    close_db = False
    if db is None and user:
        db = SessionLocal()
        close_db = True
    try:
        if user and db is not None:
            alerts = warranty_alert_items(db, user)
            context["alert_items"] = alerts
            context["alert_count"] = len(alerts)
    finally:
        if close_db and db is not None:
            db.close()
    return templates.TemplateResponse(request, template_name, context, status_code=status_code)


# Auth exceptions and dependencies

class UnauthenticatedException(Exception):
    pass

class PermissionDeniedException(Exception):
    def __init__(self, message: str = "Access Denied: Insufficient Role Permissions"):
        self.message = message

@app.exception_handler(UnauthenticatedException)
async def unauthenticated_handler(request: Request, exc: UnauthenticatedException):
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.exception_handler(PermissionDeniedException)
async def permission_denied_handler(request: Request, exc: PermissionDeniedException):
    db_session = SessionLocal()
    user = None
    try:
        user_id = request.session.get("user_id")
        if user_id:
            user = db_session.query(User).filter(User.user_id == user_id).first()
    finally:
        db_session.close()

    return templates.TemplateResponse(request, "403.html", {
        "user": user,
        "message": exc.message
    }, status_code=status.HTTP_403_FORBIDDEN)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    err_tb = traceback.format_exc()
    print(f"[500 Error on {request.url}]:\n{err_tb}", flush=True)
    try:
        with open("server_error.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- 500 ERROR on {request.url} at {datetime.now()} ---\n{err_tb}\n")
    except Exception:
        pass
    _flash(request, f"An internal error occurred: {str(exc)}", "error")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.user_id == user_id).first()

def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise UnauthenticatedException()
    return user

def require_role(*allowed_roles: str):
    def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        user = get_current_user(request, db)
        if not user:
            raise UnauthenticatedException()
        if user.role not in allowed_roles and user.role != "admin":
            raise PermissionDeniedException(f"Role '{user.role}' is not authorized to access this route.")
        return user
    return dependency


# Authentication routes
@app.get("/uploads/{filename:path}", name="uploads")
def protected_upload(filename: str, current_user: User = Depends(require_login), db: Session = Depends(get_db)):
    from pathlib import Path
    root = Path(UPLOADS_DIR).resolve()
    target = (root / filename).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if current_user.role not in ("admin", "reviewer"):
        allowed = any(Path(d.file_path).resolve() == target for d in scoped_documents(db, current_user).all())
        if not allowed and target.name.endswith("_summary_card.png"):
            cid = target.name.removesuffix("_summary_card.png")
            allowed = scoped_claims(db, current_user).filter(Claim.claim_id == cid).first() is not None
        if not allowed:
            raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(target)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if user and not verify_password(password, user.hashed_password):
        user = None
    if not user:
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid email or password. Please try again.",
            "email": email
        }, status_code=status.HTTP_400_BAD_REQUEST)
    
    request.session["user_id"] = user.user_id
    request.session["email"] = user.email
    request.session["role"] = user.role
    request.session["full_name"] = user.full_name
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "register.html", {})

@app.post("/register")
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("customer"),
    db: Session = Depends(get_db)
):
    if role not in ["customer", "service_center"]:
        role = "customer" # Enforce restricted self-registration
        
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "error": f"Email address '{email}' is already registered.",
            "full_name": full_name,
            "email": email,
            "role": role
        }, status_code=status.HTTP_400_BAD_REQUEST)
        
    count = db.query(User).count() + 1
    user_id = f"USR-{count:04d}"
    hashed_pwd = hash_password(password)
    
    new_user = User(
        user_id=user_id,
        email=email,
        hashed_password=hashed_pwd,
        full_name=full_name,
        role=role
    )
    db.add(new_user)
    write_audit(
        db,
        action="Account Created",
        performed_by=user_id,
        user_id=user_id,
        entity_type="user",
        entity_id=user_id,
        details={"email": email, "role": role},
    )
    db.commit()
    
    request.session["user_id"] = new_user.user_id
    request.session["email"] = new_user.email
    request.session["role"] = new_user.role
    request.session["full_name"] = new_user.full_name
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/health")
def health_check():
    """Quick liveness probe; also reports model readiness."""
    return {"status": "ok" if _models_ready else "loading", "models_ready": _models_ready, "python_model_ready": tabular_classifier.best_model is not None, "gtm_model_ready": vision_classifier.model is not None}


# Application routes
@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    if current_user.role == "customer":
        total_claims = db.query(Claim).filter(Claim.user_id == current_user.user_id).count()
        valid_claims = db.query(Claim).filter(Claim.user_id == current_user.user_id, Claim.final_decision == "Likely Valid").count()
        invalid_claims = db.query(Claim).filter(Claim.user_id == current_user.user_id, Claim.final_decision == "Likely Invalid").count()
        review_claims = db.query(Claim).filter(Claim.user_id == current_user.user_id, Claim.final_decision == "Manual Review Required").count()
        recent_claims = db.query(Claim).filter(Claim.user_id == current_user.user_id).order_by(Claim.created_at.desc()).limit(8).all()
        products = db.query(Product).filter(Product.user_id == current_user.user_id).order_by(Product.created_at.desc()).all()
    else:
        total_claims = db.query(Claim).count()
        valid_claims = db.query(Claim).filter(Claim.final_decision == "Likely Valid").count()
        invalid_claims = db.query(Claim).filter(Claim.final_decision == "Likely Invalid").count()
        review_claims = db.query(Claim).filter(Claim.final_decision == "Manual Review Required").count()
        recent_claims = db.query(Claim).order_by(Claim.created_at.desc()).limit(8).all()
        products = scoped_products(db, current_user).order_by(Product.created_at.desc()).limit(12).all()

    q_claim = (request.query_params.get("claim_id") or "").strip()
    q_product = (request.query_params.get("product_id") or "").strip()
    q_status = (request.query_params.get("claim_status") or "").strip()
    q_serial = (request.query_params.get("serial") or "").strip()
    q_category = (request.query_params.get("category") or "").strip()
    filtered = scoped_claims(db, current_user)
    if q_claim:
        filtered = filtered.filter(Claim.claim_id.contains(q_claim))
    if q_product:
        filtered = filtered.filter(Claim.product_id.contains(q_product))
    if q_status:
        filtered = filtered.filter(Claim.status == q_status)
    if q_claim or q_product or q_status or q_serial or q_category:
        recent_claims = filtered.order_by(Claim.created_at.desc()).limit(50).all()
        if q_serial or q_category:
            kept = []
            for c in recent_claims:
                p = db.query(Product).filter(Product.product_id == c.product_id).first()
                if q_serial and (not p or q_serial.lower() not in (p.serial_number or "").lower()):
                    continue
                if q_category and (not p or p.category != q_category):
                    continue
                kept.append(c)
            recent_claims = kept

    product_cards = [enrich_product(p) for p in products]
    pending_actions = warranty_alert_items(db, current_user)

    return render(request, "dashboard.html", {
        "user": current_user,
        "total_claims": total_claims,
        "valid_claims": valid_claims,
        "invalid_claims": invalid_claims,
        "review_claims": review_claims,
        "recent_claims": recent_claims,
        "product_cards": product_cards,
        "pending_actions": pending_actions,
        "filters": {
            "claim_id": q_claim,
            "product_id": q_product,
            "claim_status": q_status,
            "serial": q_serial,
            "category": q_category,
        },
    }, db=db)


def _require_product(db: Session, user: User, product_id: str) -> Product:
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not can_access_product(user, product):
        raise PermissionDeniedException("You cannot access this product.")
    return product


@app.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    products = scoped_products(db, current_user).count()
    claims = scoped_claims(db, current_user).count()
    return render(request, "profile.html", {
        "user": current_user,
        "product_count": products,
        "claim_count": claims,
    }, db=db)


@app.post("/profile/update")
def profile_update(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(""),
    mailing_address: str = Form(""),
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    taken = db.query(User).filter(User.email == email, User.user_id != current_user.user_id).first()
    if taken:
        _flash(request, "That email is already in use.", "error")
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    current_user.full_name = full_name.strip()
    current_user.email = email.strip()
    current_user.phone_number = phone_number.strip()
    current_user.mailing_address = mailing_address.strip()
    request.session["full_name"] = current_user.full_name
    request.session["email"] = current_user.email
    write_audit(db, action="Profile Updated", performed_by=current_user.user_id, user_id=current_user.user_id, entity_type="user", entity_id=current_user.user_id)
    db.commit()
    _flash(request, "Profile updated.")
    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/profile/change-password")
def profile_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not verify_password(current_password, current_user.hashed_password):
        _flash(request, "Current password is incorrect.", "error")
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    if len(new_password) < 8:
        _flash(request, "New password must be at least 8 characters.", "error")
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    current_user.hashed_password = hash_password(new_password)
    write_audit(db, action="Password Changed", performed_by=current_user.user_id, user_id=current_user.user_id, entity_type="user", entity_id=current_user.user_id)
    db.commit()
    _flash(request, "Password changed.")
    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/products", response_class=HTMLResponse)
def products_list(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    q_serial = (request.query_params.get("serial") or "").strip()
    q_category = (request.query_params.get("category") or "").strip()
    q_status = (request.query_params.get("warranty_status") or "").strip()
    q = scoped_products(db, current_user)
    if q_category:
        q = q.filter(Product.category == q_category)
    if q_serial:
        q = q.filter(Product.serial_number.contains(q_serial))
    cards = [enrich_product(p) for p in q.order_by(Product.created_at.desc()).all()]
    if q_status:
        cards = [c for c in cards if c["warranty_status"] == q_status]

    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(cards, page=page, per_page=per_page)

    return render(request, "products_list.html", {
        "user": current_user,
        "product_cards": pagination["items"],
        "pagination": pagination,
        "filters": {"serial": q_serial, "category": q_category, "warranty_status": q_status},
    }, db=db)


@app.get("/products/new", response_class=HTMLResponse)
def products_new_form(
    request: Request,
    current_user: User = Depends(require_role("customer", "service_center")),
):
    return render(request, "product_register.html", {"user": current_user})


@app.post("/products/new")
def products_new_submit(
    request: Request,
    product_name: str = Form(...),
    category: str = Form(...),
    brand: str = Form(...),
    model_number: str = Form(...),
    serial_number: str = Form(...),
    purchase_date: str = Form(...),
    purchase_price: float = Form(...),
    retailer: str = Form(...),
    warranty_duration_months: int = Form(24),
    has_extended_warranty: bool = Form(False),
    extended_warranty_provider: str = Form(""),
    extended_warranty_contract_number: str = Form(""),
    extended_warranty_duration_months: int = Form(0),
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db),
):
    if purchase_price < 0 or warranty_duration_months < 1:
        _flash(request, "Price cannot be negative and warranty duration must be at least 1 month.", "error")
        return RedirectResponse(url="/products/new", status_code=status.HTTP_303_SEE_OTHER)
    ext_prov = extended_warranty_provider.strip()
    ext_num = extended_warranty_contract_number.strip()
    is_ext = has_extended_warranty or bool(ext_prov or ext_num or extended_warranty_duration_months > 0)
    product_id = next_product_id(db)
    product = Product(
        product_id=product_id,
        user_id=current_user.user_id,
        product_name=product_name,
        category=category,
        brand=brand,
        model_number=model_number,
        serial_number=serial_number,
        purchase_date=purchase_date,
        purchase_price=purchase_price,
        retailer=retailer,
        warranty_duration_months=warranty_duration_months,
        has_extended_warranty=is_ext,
        extended_warranty_provider=ext_prov,
        extended_warranty_contract_number=ext_num,
        extended_warranty_duration_months=extended_warranty_duration_months,
    )
    db.add(product)
    write_audit(db, action="Product Registration", performed_by=current_user.user_id, user_id=current_user.user_id, entity_type="product", entity_id=product_id)
    db.commit()
    _flash(request, f"Product {product_id} registered.")
    return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/warranties", response_class=HTMLResponse)
def warranties_list(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    all_cards = [enrich_product(p) for p in scoped_products(db, current_user).order_by(Product.created_at.desc()).all()]
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(all_cards, page=page, per_page=per_page)
    return render(request, "warranties.html", {"user": current_user, "product_cards": pagination["items"], "pagination": pagination, "detail": None}, db=db)


@app.get("/warranties/{product_id}", response_class=HTMLResponse)
def warranty_detail(
    product_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    product = _require_product(db, current_user, product_id)
    all_cards = [enrich_product(p) for p in scoped_products(db, current_user).all()]
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(all_cards, page=page, per_page=per_page)
    return render(request, "warranties.html", {"user": current_user, "product_cards": pagination["items"], "pagination": pagination, "detail": enrich_product(product)}, db=db)


@app.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    tab = request.query_params.get("tab", "expiring").lower()
    summary = warranty_alert_summary(db, current_user)

    if tab == "expired":
        selected_items = summary["expired"]
    elif tab == "grace":
        selected_items = summary["grace"]
    elif tab == "all":
        selected_items = summary["expiring"] + summary["grace"] + summary["expired"]
    else:
        tab = "expiring"
        selected_items = summary["expiring"]

    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(selected_items, page=page, per_page=per_page)
    return render(
        request,
        "alerts.html",
        {
            "user": current_user,
            "pending_actions": pagination["items"],
            "pagination": pagination,
            "active_tab": tab,
            "summary": summary,
        },
        db=db,
    )


@app.post("/alerts/dismiss/{product_id}")
def dismiss_alert(
    product_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    tab = request.query_params.get("tab", "expiring")
    write_audit(
        db,
        action="Alert Dismissed",
        performed_by=current_user.user_id,
        user_id=current_user.user_id,
        entity_type="product",
        entity_id=product_id,
        details={"dismissed_by": current_user.email},
    )
    db.commit()
    _flash(request, f"Alert for product {product_id} dismissed.", "success")
    return RedirectResponse(url=f"/alerts?tab={tab}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/documents", response_class=HTMLResponse)
def documents_vault(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    docs_q = scoped_documents(db, current_user).order_by(Document.created_at.desc())
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(docs_q, page=page, per_page=per_page)
    docs = pagination["items"]
    products = scoped_products(db, current_user).all()
    dup_map = {}
    for doc in docs:
        others = find_hash_duplicates(db, doc.file_hash, exclude_doc_id=doc.doc_id)
        if others:
            dup_map[doc.doc_id] = others
    return render(request, "document_vault.html", {
        "user": current_user,
        "documents": docs,
        "pagination": pagination,
        "products": products,
        "dup_map": dup_map,
        "verify_doc": None,
    }, db=db)


@app.post("/documents/upload")
async def documents_upload(
    request: Request,
    product_id: str = Form(""),
    file_type: str = Form("purchase_receipt"),
    upload_file: UploadFile = File(...),
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db),
):
    contents = await upload_file.read()
    err = validate_upload(upload_file.filename, len(contents), receipt_only=True)
    if err:
        _flash(request, err, "error")
        return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)
    product = None
    if product_id:
        product = _require_product(db, current_user, product_id)
    doc_id = next_doc_id(db)
    save_name = f"{doc_id}_{upload_file.filename}"
    file_path = os.path.join("uploads", save_name)
    with open(file_path, "wb") as f:
        f.write(contents)
    file_hash = ocr_parser.compute_file_hash(contents)
    extracted = {}
    if file_type in ("purchase_receipt", "receipt", "warranty_card"):
        extracted = ocr_parser.extract_receipt_data(file_path)
    dups = find_hash_duplicates(db, file_hash)
    doc = Document(
        doc_id=doc_id,
        claim_id=None,
        product_id=product.product_id if product else None,
        user_id=current_user.user_id,
        file_name=upload_file.filename,
        file_type=file_type,
        file_path=file_path,
        file_hash=file_hash,
        extracted_data_json=json.dumps(extracted) if extracted else None,
    )
    db.add(doc)
    write_audit(
        db, action="Document Upload", performed_by=current_user.user_id, user_id=current_user.user_id,
        entity_type="document", entity_id=doc_id,
        details={"hash": file_hash, "duplicates": [d.doc_id or str(d.id) for d in dups]},
    )
    db.commit()
    if dups:
        _flash(request, f"Duplicate document hash matches {len(dups)} existing file(s).", "error")
    else:
        _flash(request, f"Document {doc_id} uploaded.")
    return RedirectResponse(url=f"/documents/{doc_id}/verify", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/documents/{doc_id}/verify", response_class=HTMLResponse)
def document_verify_page(
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    doc = scoped_documents(db, current_user).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    extracted = json.loads(doc.extracted_data_json) if doc.extracted_data_json else {}
    docs = scoped_documents(db, current_user).order_by(Document.created_at.desc()).all()
    products = scoped_products(db, current_user).all()
    dups = find_hash_duplicates(db, doc.file_hash, exclude_doc_id=doc.doc_id)
    return render(request, "document_vault.html", {
        "user": current_user,
        "documents": docs,
        "products": products,
        "verify_doc": doc,
        "extracted": extracted,
        "dup_map": {doc.doc_id: dups} if dups else {},
    }, db=db)


@app.post("/documents/{doc_id}/verify")
def document_verify_save(
    doc_id: str,
    request: Request,
    purchase_date: str = Form(""),
    invoice_number: str = Form(""),
    product_name: str = Form(""),
    model_number: str = Form(""),
    serial_number: str = Form(""),
    retailer_name: str = Form(""),
    purchase_amount: str = Form(""),
    warranty_period: str = Form(""),
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    doc = scoped_documents(db, current_user).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    original = json.loads(doc.extracted_data_json) if doc.extracted_data_json else {}
    updated = {
        "extracted_purchase_date": purchase_date,
        "extracted_invoice_number": invoice_number,
        "extracted_product_name": product_name,
        "extracted_model_number": model_number,
        "extracted_serial_number": serial_number,
        "extracted_retailer": retailer_name,
        "extracted_amount": purchase_amount,
        "extracted_warranty_period": warranty_period,
    }
    doc.extracted_data_json = json.dumps(updated)
    doc.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    doc.verified_by = current_user.user_id
    write_audit(
        db, action="OCR Correction", performed_by=current_user.user_id, user_id=current_user.user_id,
        entity_type="document", entity_id=doc_id, details={"before": original, "after": updated},
    )
    db.commit()
    _flash(request, "Extracted fields saved.")
    return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/documents/{doc_id}/delete")
def document_delete(
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    doc = scoped_documents(db, current_user).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc.file_path
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[Warn] Could not remove physical file {file_path}: {e}", flush=True)

    write_audit(
        db,
        action="Document Delete",
        performed_by=current_user.user_id,
        user_id=doc.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={"file_name": doc.file_name, "file_hash": doc.file_hash, "claim_id": doc.claim_id, "product_id": doc.product_id},
    )
    db.delete(doc)
    db.commit()
    _flash(request, f"Document {doc_id} was successfully deleted.")
    return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/documents/{doc_id}/replace")
async def document_replace(
    doc_id: str,
    request: Request,
    upload_file: UploadFile = File(...),
    file_type: Optional[str] = Form(None),
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    doc = scoped_documents(db, current_user).filter(Document.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    contents = await upload_file.read()
    err = validate_upload(upload_file.filename, len(contents), receipt_only=False)
    if err:
        _flash(request, err, "error")
        return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)

    old_file_path = doc.file_path
    old_hash = doc.file_hash
    if old_file_path and os.path.exists(old_file_path):
        try:
            os.remove(old_file_path)
        except Exception:
            pass

    save_name = f"{doc_id}_{upload_file.filename}"
    new_file_path = os.path.join("uploads", save_name)
    with open(new_file_path, "wb") as f:
        f.write(contents)
    
    new_hash = ocr_parser.compute_file_hash(contents)
    effective_file_type = file_type or doc.file_type or "purchase_receipt"

    extracted = {}
    if effective_file_type in ("purchase_receipt", "receipt", "warranty_card"):
        extracted = ocr_parser.extract_receipt_data(new_file_path)

    dups = find_hash_duplicates(db, new_hash, exclude_doc_id=doc_id)

    doc.file_name = upload_file.filename
    doc.file_path = new_file_path
    doc.file_hash = new_hash
    doc.file_type = effective_file_type
    doc.extracted_data_json = json.dumps(extracted) if extracted else None
    doc.verified_at = None
    doc.verified_by = None

    write_audit(
        db,
        action="Document Replace",
        performed_by=current_user.user_id,
        user_id=current_user.user_id,
        entity_type="document",
        entity_id=doc_id,
        details={"old_hash": old_hash, "new_hash": new_hash, "duplicates": [d.doc_id for d in dups]},
    )
    db.commit()

    if dups:
        _flash(request, f"Document {doc_id} replaced. Warning: Duplicate SHA-256 matches {len(dups)} other file(s).", "error")
    else:
        _flash(request, f"Document {doc_id} successfully replaced and re-processed.")

    if effective_file_type in ("purchase_receipt", "receipt", "warranty_card"):
        return RedirectResponse(url=f"/documents/{doc_id}/verify", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/documents", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/repairs", response_class=HTMLResponse)
def repairs_list(
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    repairs_q = scoped_repairs(db, current_user).order_by(Repair.created_at.desc())
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(repairs_q, page=page, per_page=per_page)
    products = scoped_products(db, current_user).all()
    return render(
        request,
        "repair_history.html",
        {
            "user": current_user,
            "repairs": pagination["items"],
            "pagination": pagination,
            "products": products,
        },
        db=db,
    )


@app.get("/repairs/new", response_class=HTMLResponse)
def repairs_new_form(
    request: Request,
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db),
):
    products = scoped_products(db, current_user).all()
    return render(request, "repair_history.html", {"user": current_user, "repairs": scoped_repairs(db, current_user).all(), "products": products, "show_form": True}, db=db)


@app.post("/repairs/new")
def repairs_new_submit(
    request: Request,
    product_id: str = Form(...),
    repair_date: str = Form(...),
    service_center_name: str = Form(...),
    replaced_parts: str = Form(""),
    repair_cost: float = Form(0),
    outcome: str = Form(""),
    authorized: str = Form("true"),
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db),
):
    _require_product(db, current_user, product_id)
    if repair_cost < 0:
        _flash(request, "Repair cost cannot be negative.", "error")
        return RedirectResponse(url="/repairs/new", status_code=status.HTTP_303_SEE_OTHER)
    repair_id = next_repair_id(db)
    repair = Repair(
        repair_id=repair_id,
        product_id=product_id,
        user_id=current_user.user_id,
        repair_date=repair_date,
        service_center_name=service_center_name,
        replaced_parts=replaced_parts,
        repair_cost=repair_cost,
        outcome=outcome,
        authorized=authorized.lower() in ("true", "1", "yes", "on"),
    )
    db.add(repair)
    write_audit(db, action="Repair Logged", performed_by=current_user.user_id, user_id=current_user.user_id, entity_type="repair", entity_id=repair_id)
    db.commit()
    _flash(request, f"Repair {repair_id} recorded.")
    return RedirectResponse(url="/repairs", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(
    request: Request,
    current_user: User = Depends(require_role("reviewer", "admin")),
    db: Session = Depends(get_db),
):
    action = (request.query_params.get("action") or "").strip()
    user_id = (request.query_params.get("user_id") or "").strip()
    claim_id = (request.query_params.get("claim_id") or "").strip()
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.contains(action))
    if user_id:
        q = q.filter((AuditLog.performed_by == user_id) | (AuditLog.user_id == user_id))
    if claim_id:
        q = q.filter(AuditLog.claim_id.contains(claim_id))
    
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 20)
    pagination = paginate(q.order_by(AuditLog.timestamp.desc()), page=page, per_page=per_page)

    return render(
        request,
        "audit_logs.html",
        {
            "user": current_user,
            "logs": pagination["items"],
            "pagination": pagination,
            "filters": {"action": action, "user_id": user_id, "claim_id": claim_id},
        },
        db=db,
    )


@app.get("/admin/policies", response_class=HTMLResponse)
def admin_policies(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    mapping = policy_file_map()
    selected_cat = request.query_params.get("category", "electronics")
    if selected_cat not in mapping:
        selected_cat = "electronics"

    policy_data = {}
    files = {}
    for cat, path in mapping.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                files[cat] = content
                try:
                    policy_data[cat] = json.loads(content)
                except Exception:
                    policy_data[cat] = {}
        else:
            files[cat] = "{}"
            policy_data[cat] = {}

    selected_policy = policy_data.get(selected_cat, {})
    covered_faults_text = "\n".join(selected_policy.get("covered_faults", []))
    exclusions_text = "\n".join(selected_policy.get("exclusions", []))
    mandatory_docs_text = "\n".join(selected_policy.get("mandatory_documents", []))

    global_alert_days = int(get("warranty_alert_days", 30))
    policy_alert_days = int(selected_policy.get("warranty_alert_days", global_alert_days))

    return render(
        request,
        "admin_policies.html",
        {
            "user": current_user,
            "policy_files": files,
            "categories": list(mapping.keys()),
            "selected": selected_cat,
            "policy": selected_policy,
            "warranty_alert_days": policy_alert_days,
            "global_alert_days": global_alert_days,
            "covered_faults_text": covered_faults_text,
            "exclusions_text": exclusions_text,
            "mandatory_docs_text": mandatory_docs_text,
            "policy_json_str": json.dumps(selected_policy, indent=2),
        },
        db=db,
    )


@app.post("/admin/policies/edit")
async def admin_policies_edit(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    form = await request.form()
    category = str(form.get("category", "electronics")).strip()
    mapping = policy_file_map()
    if category not in mapping:
        _flash(request, "Unknown policy category.", "error")
        return RedirectResponse(url="/admin/policies", status_code=status.HTTP_303_SEE_OTHER)

    edit_mode = str(form.get("edit_mode", "form")).strip()

    if edit_mode == "json" and form.get("policy_json"):
        policy_json = str(form.get("policy_json", ""))
        try:
            data = json.loads(policy_json)
            if "warranty_alert_days" in data:
                try:
                    save_setting("warranty_alert_days", int(data["warranty_alert_days"]))
                except Exception:
                    pass
        except json.JSONDecodeError:
            _flash(request, "Policy JSON is invalid.", "error")
            return RedirectResponse(url=f"/admin/policies?category={category}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        # Structured Text Form Mode
        target_file = mapping[category]
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data["product_category"] = category
        category_name = form.get("category_name")
        if category_name:
            data["category_name"] = str(category_name).strip()

        try:
            data["coverage_duration_months"] = int(form.get("coverage_duration_months", 24))
            data["extended_coverage_months"] = int(form.get("extended_coverage_months", 12))
            data["grace_period_days"] = int(form.get("grace_period_days", 15))
            data["reporting_deadline_days"] = int(form.get("reporting_deadline_days", 30))
            if form.get("warranty_alert_days"):
                alert_lead = int(form.get("warranty_alert_days", 30))
                data["warranty_alert_days"] = max(1, min(180, alert_lead))
                save_setting("warranty_alert_days", data["warranty_alert_days"])
        except (ValueError, TypeError) as num_err:
            _flash(request, f"Invalid number value in policy timelines: {num_err}", "error")
            return RedirectResponse(url=f"/admin/policies?category={category}", status_code=status.HTTP_303_SEE_OTHER)

        auth_svc = str(form.get("authorized_service_center_required", "true")).lower()
        data["authorized_service_center_required"] = auth_svc in ("true", "1", "yes")

        covered_text = str(form.get("covered_faults_text", ""))
        data["covered_faults"] = [line.strip() for line in covered_text.splitlines() if line.strip()]

        exclusions_text = str(form.get("exclusions_text", ""))
        data["exclusions"] = [line.strip() for line in exclusions_text.splitlines() if line.strip()]

        mandatory_docs_text = str(form.get("mandatory_documents_text", ""))
        data["mandatory_documents"] = [line.strip() for line in mandatory_docs_text.splitlines() if line.strip()]

    err = validate_policy_payload(data)
    if err:
        _flash(request, err, "error")
        return RedirectResponse(url=f"/admin/policies?category={category}", status_code=status.HTTP_303_SEE_OTHER)

    target_path = mapping[category]
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Sync to Source Code directory if present
    alt_path = os.path.join("Source Code", target_path)
    if os.path.exists(os.path.dirname(alt_path)):
        try:
            with open(alt_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        except Exception:
            pass

    policy_rule_evaluator.policies = policy_rule_evaluator._load_policies()
    write_audit(
        db,
        action="Policy Updated",
        performed_by=current_user.user_id,
        user_id=current_user.user_id,
        entity_type="policy",
        entity_id=category,
        details={"category": category, "name": data.get("category_name", category)}
    )
    db.commit()
    _flash(request, f"{data.get('category_name', category.title())} policy updated successfully.")
    return RedirectResponse(url=f"/admin/policies?category={category}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/export-csv")
def admin_export_csv(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    import io
    rows = []
    for c in db.query(Claim).order_by(Claim.created_at.desc()).all():
        p = db.query(Product).filter(Product.product_id == c.product_id).first()
        rows.append({
            "claim_id": c.claim_id,
            "product_id": c.product_id,
            "user_id": c.user_id,
            "status": c.status,
            "final_decision": c.final_decision,
            "python_predicted_class": c.python_predicted_class,
            "vision_predicted_class": c.vision_predicted_class,
            "consistency_status": c.consistency_status,
            "model_version": c.model_version,
            "serial_number": p.serial_number if p else "",
            "category": p.category if p else "",
            "claim_submission_date": c.claim_submission_date,
        })
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    write_audit(db, action="Data Export", performed_by=current_user.user_id, entity_type="export", entity_id="claims-csv")
    db.commit()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assurex_claims_export.csv"},
    )


@app.get("/claims/{claim_id}/report/pdf")
def claim_report_pdf(
    claim_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if current_user.role == "customer" and claim.user_id != current_user.user_id:
        raise PermissionDeniedException("Customers can only download their own claim reports.")
    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = json.loads(claim.decision_explanation_json) if claim.decision_explanation_json else {}
    narrative_summary = dossier.get("narrative_summary") or generate_narrative_summary(claim, product=product, dossier=dossier)
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()
    pdf_bytes = generate_claim_pdf_report(claim, product, dossier, narrative_summary=narrative_summary, documents=documents)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={claim_id}_adjudication_report.pdf"},
    )


@app.get("/claims/{claim_id}/report/print", response_class=HTMLResponse)
def claim_report_print(
    claim_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if current_user.role == "customer" and claim.user_id != current_user.user_id:
        raise PermissionDeniedException("Customers can only print their own claim reports.")
    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = json.loads(claim.decision_explanation_json) if claim.decision_explanation_json else {}
    narrative_summary = dossier.get("narrative_summary") or generate_narrative_summary(claim, product=product, dossier=dossier)
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()
    return render(
        request,
        "claim_report_printable.html",
        {
            "user": current_user,
            "claim": claim,
            "product": product,
            "dossier": dossier,
            "documents": documents,
            "narrative_summary": narrative_summary,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
        db=db,
    )


@app.get("/claims/{claim_id}/report/download")
def claim_report_download(
    claim_id: str,
    request: Request,
    format: str = "pdf",
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if current_user.role == "customer" and claim.user_id != current_user.user_id:
        raise PermissionDeniedException("Customers can only download their own claim reports.")
    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = json.loads(claim.decision_explanation_json) if claim.decision_explanation_json else {}
    narrative_summary = dossier.get("narrative_summary") or generate_narrative_summary(claim, product=product, dossier=dossier)
    documents = db.query(Document).filter(Document.claim_id == claim_id).all()

    if format.lower() == "md":
        explanation = dossier.get("explanation") or {}
        lines = [
            f"# AssureX Claim Report — {claim.claim_id}",
            "",
            "## Executive Summary",
            narrative_summary,
            "",
            f"- Product: {product.product_name if product else claim.product_id}",
            f"- Status: {claim.status}",
            f"- Final decision: {claim.final_decision}",
            f"- Model version: {claim.model_version or 'n/a'}",
            f"- Python: {claim.python_predicted_class} ({claim.python_top_confidence})",
            f"- Vision: {claim.vision_predicted_class} ({claim.vision_top_confidence})",
            f"- Consistency: {claim.consistency_status}",
            "",
            "## Supporting factors",
            *[f"- {x}" for x in explanation.get("supporting_factors", []) or ["None"]],
            "",
            "## Opposing factors",
            *[f"- {x}" for x in explanation.get("opposing_factors", []) or ["None"]],
            "",
            "## Reviewer comments",
            claim.reviewer_comments or "None",
        ]
        body = "\n".join(lines)
        return StreamingResponse(
            iter([body]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={claim_id}_report.md"},
        )

    pdf_bytes = generate_claim_pdf_report(claim, product, dossier, narrative_summary=narrative_summary, documents=documents)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={claim_id}_adjudication_report.pdf"},
    )



@app.get("/claims/new", response_class=HTMLResponse)
def new_claim_form(
    request: Request,
    product_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db)
):
    products = scoped_products(db, current_user).order_by(Product.created_at.desc()).all()
    selected = None
    draft_claim = None
    if draft_id:
        draft_claim = scoped_claims(db, current_user).filter(Claim.claim_id == draft_id).first()
        if draft_claim and not product_id:
            product_id = draft_claim.product_id

    if product_id:
        selected = scoped_products(db, current_user).filter(Product.product_id == product_id).first()
    vault_docs = []
    if selected:
        vault_docs = db.query(Document).filter(Document.product_id == selected.product_id).all()
    return render(request, "claim_intake.html", {
        "user": current_user,
        "products": products,
        "selected_product": selected,
        "vault_docs": vault_docs,
        "draft_claim": draft_claim,
        "today": datetime.now().strftime("%Y-%m-%d"),
    }, db=db)


def _wait_models():
    wait_deadline = int(get("model_ready_timeout_seconds", 15))
    waited = 0
    while not _models_ready and waited < wait_deadline:
        time.sleep(0.5)
        waited += 0.5
    if not _models_ready:
        raise HTTPException(status_code=503, detail="Models still loading. Retry in a moment.")


def _build_claim_dict_from_product(product: Product, extra: dict, db: Session) -> dict:
    prev_count, has_unauth = repair_stats_for_product(db, product.product_id)
    payload = product_to_claim_dict(product)
    payload.update(extra)
    if extra.get("previous_repairs_count") is None:
        payload["previous_repairs_count"] = prev_count
    if extra.get("has_unauthorized_repairs") is None:
        payload["has_unauthorized_repairs"] = has_unauth
    else:
        payload["has_unauthorized_repairs"] = extra.get("has_unauthorized_repairs") or has_unauth
    return payload


@app.post("/claims/pre-check")
async def claims_pre_check(
    request: Request,
    product_id: str = Form(...),
    fault_occurrence_date: str = Form(...),
    claim_submission_date: str = Form(None),
    fault_category: str = Form("general_defect"),
    damage_type: str = Form("none"),
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db)
):
    product = scoped_products(db, current_user).filter(Product.product_id == product_id).first()
    if not product:
        return JSONResponse({"ready": False, "error": "Select a registered product first."}, status_code=400)
    submit_date = claim_submission_date or datetime.now().strftime("%Y-%m-%d")
    docs = db.query(Document).filter(Document.product_id == product_id).all()
    present = documents_by_policy_key(docs)
    policy = load_policy(product.category)
    mandatory = policy.get("mandatory_documents", [])
    missing = [m for m in mandatory if m not in present]
    prev_count, has_unauth = repair_stats_for_product(db, product.product_id)
    raw = product_to_claim_dict(product)
    raw.update({
        "fault_occurrence_date": fault_occurrence_date,
        "claim_submission_date": submit_date,
        "fault_category": fault_category,
        "damage_type": damage_type,
        "previous_repairs_count": prev_count,
        "has_unauthorized_repairs": has_unauth,
        "has_receipt": "purchase_receipt" in present or "receipt" in present,
        "has_warranty_card": "warranty_card" in present,
        "has_product_photo": "product_image" in present,
        "has_serial_photo": "serial_number_photo" in present,
        "missing_documents_count": len(missing),
    })
    derived = compute_derived_claim_features(raw)
    contradictions = ContradictionAndDuplicateDetector.detect_contradictions(derived)
    rule_eval = policy_rule_evaluator.evaluate_claim(derived)
    warnings = list(rule_eval.get("warnings") or [])
    if derived.get("remaining_warranty_days", 0) <= int(get("warranty_alert_days", 30)):
        warnings.append("Warranty is expired, in grace, or inside the alert window.")
    actions = []
    if missing:
        actions.append(f"Upload missing documents: {', '.join(missing)}")
    if contradictions["has_contradictions"]:
        actions.extend(contradictions["contradictions"])
    ready = not missing and not contradictions["has_contradictions"]
    return JSONResponse({
        "ready": ready,
        "missing_documents": missing,
        "warnings": warnings,
        "contradictions": contradictions["contradictions"],
        "recommended_actions": actions,
        "remaining_warranty_days": derived.get("remaining_warranty_days"),
        "serial_match_status": derived.get("serial_match_status"),
    })


@app.post("/claims/submit")
async def submit_claim(
    request: Request,
    product_id: str = Form(""),
    product_name: str = Form(""),
    product_category: str = Form("electronics"),
    brand: str = Form(""),
    model_number: str = Form(""),
    serial_number: str = Form(""),
    purchase_date: str = Form(""),
    purchase_price: float = Form(0),
    retailer: str = Form(""),
    warranty_months: int = Form(24),
    has_extended_warranty: bool = Form(False),
    extended_warranty_provider: str = Form(""),
    extended_warranty_contract_number: str = Form(""),
    extended_warranty_duration_months: int = Form(0),
    fault_category: str = Form("motherboard_failure"),
    damage_type: str = Form("none"),
    fault_occurrence_date: str = Form(""),
    claim_submission_date: str = Form(datetime.now().strftime("%Y-%m-%d")),
    description: str = Form(""),
    previous_repairs_count: Optional[int] = Form(None),
    has_unauthorized_repairs: bool = Form(False),
    receipt_file: Optional[UploadFile] = File(None),
    warranty_card_file: Optional[UploadFile] = File(None),
    product_photo_file: Optional[UploadFile] = File(None),
    serial_photo_file: Optional[UploadFile] = File(None),
    damage_photo_file: Optional[UploadFile] = File(None),
    attach_doc_ids: str = Form(""),
    action_type: str = Form("submit"),
    draft_id: Optional[str] = Form(None),
    current_user: User = Depends(require_role("customer", "service_center")),
    db: Session = Depends(get_db)
):
    is_draft = (action_type.lower() == "draft")
    if not is_draft:
        _wait_models()
        if not fault_occurrence_date:
            _flash(request, "Fault occurrence date is required.", "error")
            return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)
    else:
        if not fault_occurrence_date:
            fault_occurrence_date = datetime.now().strftime("%Y-%m-%d")

    os.makedirs("uploads", exist_ok=True)

    try:
        product = None
        if product_id:
            product = scoped_products(db, current_user).filter(Product.product_id == product_id).first()
            if not product:
                _flash(request, "Selected product was not found.", "error")
                return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)

        if not product:
            if is_draft and not product_name:
                product = scoped_products(db, current_user).first()
            if not product:
                if not product_name or not serial_number or not purchase_date:
                    _flash(request, "Register a product first or complete the new-product fields.", "error")
                    return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)
                product_id = next_product_id(db)
                product = Product(
                    product_id=product_id,
                    user_id=current_user.user_id,
                    product_name=product_name,
                    category=product_category,
                    brand=brand or "Generic",
                    model_number=model_number or "N/A",
                    serial_number=serial_number,
                    purchase_date=purchase_date,
                    purchase_price=purchase_price or 0,
                    retailer=retailer or "Unknown",
                    warranty_duration_months=warranty_months,
                    has_extended_warranty=has_extended_warranty or bool(extended_warranty_provider or extended_warranty_contract_number or extended_warranty_duration_months > 0),
                    extended_warranty_provider=extended_warranty_provider.strip(),
                    extended_warranty_contract_number=extended_warranty_contract_number.strip(),
                    extended_warranty_duration_months=extended_warranty_duration_months,
                )
                db.add(product)
                db.flush()
                write_audit(
                    db, action="Product Registration", performed_by=current_user.user_id,
                    user_id=current_user.user_id, entity_type="product", entity_id=product_id,
                    details={"via": "claim_submit"},
                )

        user_id = current_user.user_id
        db_claim = None
        if draft_id:
            db_claim = scoped_claims(db, current_user).filter(Claim.claim_id == draft_id).first()

        if db_claim:
            claim_id = db_claim.claim_id
        else:
            max_id = db.query(Claim.id).order_by(Claim.id.desc()).first()
            next_num = (max_id[0] + 1) if max_id else 1
            while db.query(Claim).filter(Claim.claim_id == f"CLM-2026-{next_num:04d}").first():
                next_num += 1
            claim_id = f"CLM-2026-{next_num:04d}"

        uploads = [
            (receipt_file, "purchase_receipt"),
            (warranty_card_file, "warranty_card"),
            (product_photo_file, "product_image"),
            (serial_photo_file, "serial_number_photo"),
            (damage_photo_file, "damage_photo"),
        ]
        file_hash = ""
        ocr_extracted = {}
        pending_docs = []

        for upload, ftype in uploads:
            if not upload or not upload.filename:
                continue
            contents = await upload.read()
            err = validate_upload(upload.filename, len(contents), receipt_only=(ftype in ("purchase_receipt", "warranty_card")))
            if err:
                _flash(request, err, "error")
                return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)
            clean_filename = os.path.basename(upload.filename)
            save_name = f"{claim_id}_{ftype}_{clean_filename}"
            file_path = os.path.join("uploads", save_name)
            with open(file_path, "wb") as f:
                f.write(contents)
            h = ocr_parser.compute_file_hash(contents)
            extracted = {}
            if ftype == "purchase_receipt":
                try:
                    extracted = ocr_parser.extract_receipt_data(file_path)
                except Exception as ocr_err:
                    print(f"Warning: OCR extraction failed: {ocr_err}")
                    extracted = {}
                ocr_extracted = extracted
                file_hash = h
            pending_docs.append({
                "file_name": clean_filename,
                "file_type": ftype,
                "file_path": file_path,
                "file_hash": h,
                "extracted": extracted,
            })

        if is_draft:
            if not db_claim:
                db_claim = Claim(
                    claim_id=claim_id,
                    user_id=user_id,
                    product_id=product.product_id,
                    fault_category=fault_category or "motherboard_failure",
                    damage_type=damage_type or "none",
                    fault_occurrence_date=fault_occurrence_date,
                    claim_submission_date=claim_submission_date,
                    description=description,
                    status="Draft",
                    final_decision="Draft",
                    decision_explanation_json=json.dumps({"notes": "Claim saved as draft."}),
                    document_hash=file_hash,
                    extended_warranty_provider=extended_warranty_provider.strip() or getattr(product, "extended_warranty_provider", ""),
                    extended_warranty_contract_number=extended_warranty_contract_number.strip() or getattr(product, "extended_warranty_contract_number", ""),
                    model_version=str(get("model_version", "v2")),
                )
                db.add(db_claim)
            else:
                db_claim.product_id = product.product_id
                db_claim.fault_category = fault_category or "motherboard_failure"
                db_claim.damage_type = damage_type or "none"
                db_claim.fault_occurrence_date = fault_occurrence_date
                db_claim.claim_submission_date = claim_submission_date
                db_claim.description = description
                record_status_transition(
                    db, db_claim, "Draft",
                    actor_user_id=user_id, actor_role=current_user.role, note="Draft saved",
                )
                db_claim.final_decision = "Draft"
                if extended_warranty_provider.strip():
                    db_claim.extended_warranty_provider = extended_warranty_provider.strip()
                if extended_warranty_contract_number.strip():
                    db_claim.extended_warranty_contract_number = extended_warranty_contract_number.strip()

            db.flush()
            ensure_initial_status(
                db, db_claim, actor_user_id=user_id, actor_role=current_user.role, note="Draft saved"
            )
            for pd_item in pending_docs:
                doc = Document(
                    doc_id=next_doc_id(db),
                    claim_id=claim_id,
                    product_id=product.product_id,
                    user_id=user_id,
                    file_name=pd_item["file_name"],
                    file_type=pd_item["file_type"],
                    file_path=pd_item["file_path"],
                    file_hash=pd_item["file_hash"],
                    extracted_data_json=json.dumps(pd_item["extracted"]) if pd_item["extracted"] else None,
                )
                db.add(doc)
                db.flush()
            if attach_doc_ids:
                for did in [x.strip() for x in attach_doc_ids.split(",") if x.strip()]:
                    existing = scoped_documents(db, current_user).filter(Document.doc_id == did).first()
                    if existing:
                        existing.claim_id = claim_id
                        existing.product_id = product.product_id
            write_audit(
                db, action="Claim Draft Saved", performed_by=user_id, user_id=user_id,
                claim_id=claim_id, entity_type="claim", entity_id=claim_id,
                details={"status": "Draft"},
            )
            db.commit()
            _flash(request, f"Claim {claim_id} saved as draft.")
            return RedirectResponse(url=f"/claims/view/{claim_id}", status_code=status.HTTP_303_SEE_OTHER)

        # Full Submission
        present_keys = documents_by_policy_key(
            db.query(Document).filter(Document.product_id == product.product_id).all()
        )
        for pd_item in pending_docs:
            present_keys.add(pd_item["file_type"])
            mapped = FILE_TYPE_MAP.get(pd_item["file_type"], pd_item["file_type"])
            present_keys.add(mapped)

        policy = load_policy(product.category)
        missing_mandatory = [
            doc for doc in policy.get("mandatory_documents", []) if doc not in present_keys
        ]

        raw_payload = {}
        try:
            form_data = await request.form()
            raw_payload.update({k: v for k, v in dict(form_data).items() if not hasattr(v, "filename")})
        except Exception:
            pass

        ocr_serial = ocr_extracted.get("extracted_serial_number") or product.serial_number
        extra = {
            "claim_id": claim_id,
            "user_id": user_id,
            "fault_occurrence_date": fault_occurrence_date,
            "claim_submission_date": claim_submission_date,
            "fault_category": fault_category,
            "damage_type": damage_type,
            "description": description,
            "ocr_serial_number": ocr_serial,
            "document_hash": file_hash,
            "has_receipt": "purchase_receipt" in present_keys,
            "has_warranty_card": "warranty_card" in present_keys,
            "has_product_photo": "product_image" in present_keys,
            "has_serial_photo": "serial_number_photo" in present_keys,
            "missing_documents_count": len(missing_mandatory),
            "previous_repairs_count": previous_repairs_count,
            "has_unauthorized_repairs": has_unauthorized_repairs,
            "has_extended_warranty": has_extended_warranty or bool(extended_warranty_provider or extended_warranty_contract_number or extended_warranty_duration_months > 0) or getattr(product, "has_extended_warranty", False),
            "extended_warranty_provider": extended_warranty_provider.strip() or getattr(product, "extended_warranty_provider", ""),
            "extended_warranty_contract_number": extended_warranty_contract_number.strip() or getattr(product, "extended_warranty_contract_number", ""),
            "extended_warranty_duration_months": extended_warranty_duration_months or getattr(product, "extended_warranty_duration_months", 0),
        }
        raw_payload.update(_build_claim_dict_from_product(product, extra, db))
        claim_dict = compute_derived_claim_features(raw_payload)

        py_result = tabular_classifier.predict_single(claim_dict)
        card_img = render_claim_card(pd.Series(claim_dict), variation_id=1)
        started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        card_path = os.path.join("uploads", f"{claim_id}_summary_card.png")
        card_img.save(card_path)
        vis_result = vision_classifier.predict_image(card_img)

        existing_claims_db = [c.__dict__ for c in db.query(Claim).all()]
        dossier = fusion_engine.evaluate_full_claim(claim_dict, py_result, vis_result, existing_claims_db)
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)

        comp = dossier["comparison"]
        final_dec = dossier["final_decision"]
        model_version = str(get("model_version", "v2"))

        if final_dec == "Manual Review Required":
            claim_status = "Manual Review"
        elif final_dec == "Likely Valid":
            claim_status = "Approved"
        else:
            claim_status = "Rejected"

        if not db_claim:
            db_claim = Claim(
                claim_id=claim_id,
                user_id=user_id,
                product_id=product.product_id,
                fault_category=fault_category,
                damage_type=damage_type,
                fault_occurrence_date=fault_occurrence_date,
                claim_submission_date=claim_submission_date,
                description=description,
                status="Draft",
                python_predicted_class=py_result["predicted_class"],
                python_top_confidence=py_result["top_confidence"],
                vision_predicted_class=vis_result["predicted_class"],
                vision_top_confidence=vis_result["top_confidence"],
                confidence_difference=comp["confidence_difference"],
                consistency_status=comp["consistency_status"],
                final_decision=final_dec,
                decision_explanation_json=json.dumps(dossier),
                document_hash=file_hash,
                extended_warranty_provider=extra["extended_warranty_provider"],
                extended_warranty_contract_number=extra["extended_warranty_contract_number"],
                model_version=model_version,
            )
            db.add(db_claim)
        else:
            db_claim.product_id = product.product_id
            db_claim.fault_category = fault_category
            db_claim.damage_type = damage_type
            db_claim.fault_occurrence_date = fault_occurrence_date
            db_claim.claim_submission_date = claim_submission_date
            db_claim.description = description
            db_claim.python_predicted_class = py_result["predicted_class"]
            db_claim.python_top_confidence = py_result["top_confidence"]
            db_claim.vision_predicted_class = vis_result["predicted_class"]
            db_claim.vision_top_confidence = vis_result["top_confidence"]
            db_claim.confidence_difference = comp["confidence_difference"]
            db_claim.consistency_status = comp["consistency_status"]
            db_claim.final_decision = final_dec
            db_claim.decision_explanation_json = json.dumps(dossier)
            db_claim.document_hash = file_hash
            db_claim.extended_warranty_provider = extra["extended_warranty_provider"]
            db_claim.extended_warranty_contract_number = extra["extended_warranty_contract_number"]
            db_claim.model_version = model_version

        db.flush()
        record_submission_stages(
            db, db_claim, claim_status,
            started_at=started_at, finished_at=finished_at,
            actor_user_id=user_id, actor_role=current_user.role,
        )
        for pd_item in pending_docs:
            doc = Document(
                doc_id=next_doc_id(db),
                claim_id=claim_id,
                product_id=product.product_id,
                user_id=user_id,
                file_name=pd_item["file_name"],
                file_type=pd_item["file_type"],
                file_path=pd_item["file_path"],
                file_hash=pd_item["file_hash"],
                extracted_data_json=json.dumps(pd_item["extracted"]) if pd_item["extracted"] else None,
            )
            db.add(doc)
            db.flush()
            write_audit(
                db, action="Document Upload", performed_by=user_id, user_id=user_id,
                claim_id=claim_id, entity_type="document", entity_id=doc.doc_id,
                details={"file_type": pd_item["file_type"], "hash": pd_item["file_hash"]},
            )
        if attach_doc_ids:
            for did in [x.strip() for x in attach_doc_ids.split(",") if x.strip()]:
                existing = scoped_documents(db, current_user).filter(Document.doc_id == did).first()
                if existing:
                    existing.claim_id = claim_id
                    existing.product_id = product.product_id
        write_audit(
            db, action="AI Inference", performed_by=user_id, user_id=user_id,
            claim_id=claim_id, entity_type="claim", entity_id=claim_id,
            details={"final_decision": final_dec, "model_version": model_version},
        )
        write_audit(
            db, action="Status Change", performed_by="system", user_id=user_id,
            claim_id=claim_id, entity_type="claim", entity_id=claim_id,
            details={"status": claim_status},
        )
        write_audit(
            db, action="Alert Claimed", performed_by=user_id, user_id=user_id,
            claim_id=claim_id, entity_type="product", entity_id=product.product_id,
            details={"via": "claim_submit"},
        )
        db.commit()

        return RedirectResponse(url=f"/claims/view/{claim_id}", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as exc:
        db.rollback()
        import traceback
        err_trace = traceback.format_exc()
        print(f"[Error in /claims/submit]:\n{err_trace}", flush=True)
        try:
            with open("server_error.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- ERROR in /claims/submit at {datetime.now()} ---\n{err_trace}\n")
        except Exception:
            pass
        _flash(request, f"Error submitting claim: {str(exc)}", "error")
        return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/claims/submit")
def claims_submit_get():
    return RedirectResponse(url="/claims/new", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/claims/import-csv", response_class=HTMLResponse)
def import_csv_page(
    request: Request,
    current_user: User = Depends(require_role("customer", "service_center", "admin"))
):
    return templates.TemplateResponse(request, "import_csv.html", {"user": current_user})

@app.post("/claims/import-csv")
async def import_csv_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("customer", "service_center", "admin")),
    db: Session = Depends(get_db)
):
    import io
    
    # Guard: wait for background model loading
    wait_deadline = 15
    waited = 0
    while not _models_ready and waited < wait_deadline:
        time.sleep(0.5)
        waited += 0.5
    if not _models_ready:
        raise HTTPException(status_code=503, detail="Models still loading. Retry in a moment.")

    if not file.filename.endswith('.csv'):
        return templates.TemplateResponse(request, "import_csv.html", {
            "user": current_user,
            "error": "Uploaded file must be a .csv file."
        })

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        return templates.TemplateResponse(request, "import_csv.html", {
            "user": current_user,
            "error": f"Failed to parse CSV file: {e}"
        })

    imported_count = 0
    now_tag = datetime.now().strftime("%m%d%H%M%S")

    for idx, row in df.iterrows():
        try:
            raw_claim_id = str(row.get("claim_id", "")).strip()
            if not raw_claim_id or raw_claim_id.lower() == "nan" or db.query(Claim).filter(Claim.claim_id == raw_claim_id).first():
                claim_id = f"CLM-{now_tag}-{idx:04d}"
            else:
                claim_id = raw_claim_id

            raw_prod_id = str(row.get("product_id", "")).strip()
            if not raw_prod_id or raw_prod_id.lower() == "nan" or db.query(Product).filter(Product.product_id == raw_prod_id).first():
                product_id = f"PRD-{now_tag}-{idx:04d}"
            else:
                product_id = raw_prod_id

            raw_user_id = str(row.get("user_id", "")).strip()
            if raw_user_id and raw_user_id.lower() != "nan" and db.query(User).filter(User.user_id == raw_user_id).first():
                user_id = raw_user_id
            else:
                user_id = current_user.user_id

            product_name = str(row.get("product_name", "Warranty Product"))
            product_category = str(row.get("product_category", "electronics"))
            brand = str(row.get("brand", "Generic"))
            model_number = str(row.get("model_number", "MOD-100"))
            serial_number = str(row.get("user_serial_number", row.get("serial_number", f"SN-{now_tag}-{idx:04d}")))
            ocr_serial = str(row.get("ocr_serial_number", serial_number))

            purchase_date = str(row.get("purchase_date", "2024-01-01"))
            try:
                purchase_price = float(row.get("purchase_price", 500.0))
            except Exception:
                purchase_price = 500.0

            retailer = str(row.get("retailer", "Retailer Store"))
            try:
                warranty_months = int(row.get("warranty_duration_months", 24))
            except Exception:
                warranty_months = 24

            fault_category = str(row.get("fault_category", "Hardware Defect"))
            damage_type = str(row.get("damage_type", "none"))
            fault_occurrence_date = str(row.get("fault_occurrence_date", "2025-05-01"))
            claim_submission_date = str(row.get("claim_submission_date", datetime.now().strftime("%Y-%m-%d")))
            description = str(row.get("description", "Imported claim record from CSV"))
            try:
                prev_repairs = int(row.get("previous_repairs_count", 0) or 0)
            except Exception:
                prev_repairs = 0
            has_unauth = str(row.get("has_unauthorized_repairs", False)).strip().lower() in ("true", "1", "yes")

            row_dict = row.to_dict()
            row_dict.update({
                "claim_id": claim_id,
                "user_id": user_id,
                "product_id": product_id,
                "product_name": product_name,
                "product_category": product_category,
                "brand": brand,
                "model_number": model_number,
                "user_serial_number": serial_number,
                "ocr_serial_number": ocr_serial,
                "purchase_date": purchase_date,
                "purchase_price": purchase_price,
                "retailer": retailer,
                "warranty_duration_months": warranty_months,
                "fault_occurrence_date": fault_occurrence_date,
                "claim_submission_date": claim_submission_date,
                "fault_category": fault_category,
                "damage_type": damage_type,
                "previous_repairs_count": prev_repairs,
                "has_unauthorized_repairs": has_unauth,
            })

            claim_dict = compute_derived_claim_features(row_dict)

            # Predict with tabular model & render summary card for vision model
            py_result = tabular_classifier.predict_single(claim_dict)
            card_img = render_claim_card(pd.Series(claim_dict), variation_id=1)
            card_path = os.path.join("uploads", f"{claim_id}_summary_card.png")
            card_img.save(card_path)
            vis_result = vision_classifier.predict_image(card_img)

            existing_claims_db = [c.__dict__ for c in db.query(Claim).all()]
            dossier = fusion_engine.evaluate_full_claim(claim_dict, py_result, vis_result, existing_claims_db)

            comp = dossier["comparison"]
            final_dec = dossier["final_decision"]

            db_product = Product(
                product_id=product_id,
                user_id=user_id,
                product_name=product_name,
                category=product_category,
                brand=brand,
                model_number=model_number,
                serial_number=serial_number,
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                retailer=retailer,
                warranty_duration_months=warranty_months
            )
            db.add(db_product)

            db_claim = Claim(
                claim_id=claim_id,
                user_id=user_id,
                product_id=product_id,
                fault_category=fault_category,
                damage_type=damage_type,
                fault_occurrence_date=fault_occurrence_date,
                claim_submission_date=claim_submission_date,
                description=description,
                status="Draft",
                python_predicted_class=py_result["predicted_class"],
                python_top_confidence=py_result["top_confidence"],
                vision_predicted_class=vis_result["predicted_class"],
                vision_top_confidence=vis_result["top_confidence"],
                confidence_difference=comp["confidence_difference"],
                consistency_status=comp["consistency_status"],
                final_decision=final_dec,
                decision_explanation_json=json.dumps(dossier),
                model_version=str(get("model_version", "v2")),
            )
            db.add(db_claim)
            db.flush()
            record_submission_stages(
                db,
                db_claim,
                "Manual Review" if final_dec == "Manual Review Required" else ("Approved" if final_dec == "Likely Valid" else "Rejected"),
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
                actor_user_id=user_id,
                actor_role=current_user.role,
            )
            db.commit()
            imported_count += 1
        except Exception as row_err:
            db.rollback()
            print(f"[import] Error processing row {idx}: {row_err}", flush=True)
            continue

    return RedirectResponse(url=f"/?imported={imported_count}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/claims/view/{claim_id}", response_class=HTMLResponse)
def view_claim_dossier(
    claim_id: str,
    request: Request,
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    if current_user.role == "customer" and claim.user_id != current_user.user_id:
        raise PermissionDeniedException("Customers can only view dossiers for their own claims.")

    product = db.query(Product).filter(Product.product_id == claim.product_id).first()
    dossier = json.loads(claim.decision_explanation_json) if claim.decision_explanation_json else {}
    narrative_summary = dossier.get("narrative_summary") or generate_narrative_summary(claim, product=product, dossier=dossier)
    card_url = f"/uploads/{claim_id}_summary_card.png"
    return render(request, "dossier.html", {
        "user": current_user,
        "claim": claim,
        "product": product,
        "dossier": dossier,
        "narrative_summary": narrative_summary,
        "card_url": card_url
    }, db=db)

@app.get("/reviewer/queue", response_class=HTMLResponse)
def reviewer_queue(
    request: Request,
    current_user: User = Depends(require_role("reviewer")),
    db: Session = Depends(get_db)
):
    claims_q = db.query(Claim).filter(Claim.status.in_(["Manual Review", "Request More Info"])).order_by(Claim.created_at.desc())
    page = request.query_params.get("page", 1)
    per_page = request.query_params.get("per_page", 15)
    pagination = paginate(claims_q, page=page, per_page=per_page)
    return templates.TemplateResponse(request, "reviewer_queue.html", {
        "user": current_user,
        "review_claims": pagination["items"],
        "pagination": pagination,
    })

@app.post("/reviewer/override/{claim_id}")
def reviewer_override(
    request: Request,
    claim_id: str,
    override_action: str = Form(...), # Approved, Rejected, Request More Info, Closed
    comments: str = Form(...),
    current_user: User = Depends(require_role("reviewer", "admin")),
    db: Session = Depends(get_db)
):
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    if override_action not in {"Approved", "Rejected", "Request More Info", "Closed"}:
        raise HTTPException(status_code=400, detail="Invalid reviewer action")
    if not comments.strip():
        raise HTTPException(status_code=400, detail="Reviewer comments are required")
    record_status_transition(
        db, claim, override_action,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
        note=comments,
    )
    claim.reviewer_comments = comments
    claim.reviewed_by = f"{current_user.full_name} ({current_user.role.capitalize()})"
    claim.override_flag = True
    
    # Audit log entry
    audit = AuditLog(
        claim_id=claim_id,
        user_id=current_user.user_id,
        entity_type="claim",
        entity_id=claim_id,
        action=f"Reviewer Override -> {override_action}",
        performed_by=current_user.user_id,
        details_json=json.dumps({"comments": comments, "original_decision": claim.final_decision, "new_status": override_action})
    )
    db.add(audit)
    db.commit()
    
    _flash(request, f"Claim status updated to '{override_action}'.")
    return RedirectResponse(url=f"/claims/view/{claim_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    total = db.query(Claim).count()
    valid = db.query(Claim).filter(Claim.final_decision == "Likely Valid").count()
    invalid = db.query(Claim).filter(Claim.final_decision == "Likely Invalid").count()
    review = db.query(Claim).filter(Claim.final_decision == "Manual Review Required").count()
    
    disagreements = db.query(Claim).filter(Claim.consistency_status == "Model Disagreement").count()
    
    all_claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
    
    return templates.TemplateResponse(request, "analytics.html", {
        "user": current_user,
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "review": review,
        "disagreements": disagreements,
        "all_claims": all_claims
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
