"""
AssureX Claim Engine - Database Schema & Seed Script
SQLAlchemy ORM models for Users, Products, Claims, Documents, Repairs, and Audit Logs.
Database: SQLite ('database/assurex.db')
"""

import os
import hashlib
import hmac
import secrets
from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

def _resolve_db_path():
    override = os.environ.get("ASSUREX_DB_PATH")
    if override:
        os.makedirs(os.path.dirname(os.path.abspath(override)), exist_ok=True)
        return os.path.abspath(override)
    candidates = [
        os.path.join(BASE_DIR, "database", "assurex.db"),
        os.path.join(BASE_DIR, "02. Complete Source Code", "database", "assurex.db"),
        os.path.abspath(os.path.join("database", "assurex.db")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    target = os.path.join(BASE_DIR, "database", "assurex.db")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    return target

DB_PATH = _resolve_db_path()
DB_DIR = os.path.dirname(DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return f"pbkdf2_sha256$260000${salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        if stored.startswith("pbkdf2_sha256$"):
            _, rounds, salt, digest = stored.split("$")
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
            return hmac.compare_digest(actual, digest)
        return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)
    except (ValueError, TypeError):
        return False

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False, default="customer")
    phone_number = Column(String(50), nullable=True, default="")
    mailing_address = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=_utcnow)

    products = relationship("Product", back_populates="owner")
    claims = relationship("Claim", back_populates="claimant")
    documents = relationship("Document", back_populates="owner")
    repairs = relationship("Repair", back_populates="owner")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    product_name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False)
    brand = Column(String(50), nullable=False)
    model_number = Column(String(50), nullable=False)
    serial_number = Column(String(50), nullable=False)
    purchase_date = Column(String(20), nullable=False)
    purchase_price = Column(Float, nullable=False)
    retailer = Column(String(100), nullable=False)
    warranty_duration_months = Column(Integer, nullable=False, default=24)
    has_extended_warranty = Column(Boolean, default=False)
    extended_warranty_provider = Column(String(100), nullable=True)
    extended_warranty_contract_number = Column(String(100), nullable=True)
    extended_warranty_duration_months = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=_utcnow)

    owner = relationship("User", back_populates="products")
    claims = relationship("Claim", back_populates="product")
    documents = relationship("Document", back_populates="product")
    repairs = relationship("Repair", back_populates="product")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)

    fault_category = Column(String(100), nullable=False)
    damage_type = Column(String(100), default="none")
    fault_occurrence_date = Column(String(20), nullable=False)
    claim_submission_date = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(50), default="Submitted")

    python_predicted_class = Column(String(50), nullable=True)
    python_top_confidence = Column(Float, nullable=True)
    vision_predicted_class = Column(String(50), nullable=True)
    vision_top_confidence = Column(Float, nullable=True)
    confidence_difference = Column(Float, nullable=True)
    consistency_status = Column(String(50), nullable=True)

    final_decision = Column(String(50), nullable=True)
    decision_explanation_json = Column(Text, nullable=True)

    reviewer_comments = Column(Text, nullable=True)
    reviewed_by = Column(String(50), nullable=True)
    override_flag = Column(Boolean, default=False)

    document_hash = Column(String(100), nullable=True)
    extended_warranty_provider = Column(String(100), nullable=True)
    extended_warranty_contract_number = Column(String(100), nullable=True)
    model_version = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    claimant = relationship("User", back_populates="claims")
    product = relationship("Product", back_populates="claims")
    documents = relationship("Document", back_populates="claim")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(50), unique=True, index=True, nullable=True)
    claim_id = Column(String(50), ForeignKey("claims.claim_id"), nullable=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=True)
    file_name = Column(String(150), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_hash = Column(String(100), nullable=False)
    extracted_data_json = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    claim = relationship("Claim", back_populates="documents")
    product = relationship("Product", back_populates="documents")
    owner = relationship("User", back_populates="documents")

class Repair(Base):
    __tablename__ = "repairs"

    id = Column(Integer, primary_key=True, index=True)
    repair_id = Column(String(50), unique=True, index=True, nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    repair_date = Column(String(20), nullable=False)
    service_center_name = Column(String(150), nullable=False)
    replaced_parts = Column(String(255), nullable=True)
    repair_cost = Column(Float, nullable=True, default=0.0)
    outcome = Column(String(100), nullable=True)
    authorized = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    product = relationship("Product", back_populates="repairs")
    owner = relationship("User", back_populates="repairs")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), nullable=True)
    user_id = Column(String(50), nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    performed_by = Column(String(50), nullable=False)
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)


class ClaimStatusHistory(Base):
    __tablename__ = "claim_status_history"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String(50), ForeignKey("claims.claim_id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    actor_user_id = Column(String(50), ForeignKey("users.user_id"), nullable=True)
    actor_role = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    claim_id = Column(String(50), nullable=True)
    product_id = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)


def _table_columns(inspector, table_name):
    if table_name not in inspector.get_table_names():
        return {}
    return {c["name"]: c for c in inspector.get_columns(table_name)}


def migrate_schema():
    """Add missing columns/tables on existing SQLite files without dropping data."""
    inspector = inspect(engine)
    statements = []

    claim_cols = _table_columns(inspector, "claims")
    if claim_cols:
        if "model_version" not in claim_cols:
            statements.append("ALTER TABLE claims ADD COLUMN model_version VARCHAR(20)")
        if "extended_warranty_provider" not in claim_cols:
            statements.append("ALTER TABLE claims ADD COLUMN extended_warranty_provider VARCHAR(100) DEFAULT ''")
        if "extended_warranty_contract_number" not in claim_cols:
            statements.append("ALTER TABLE claims ADD COLUMN extended_warranty_contract_number VARCHAR(100) DEFAULT ''")

    prod_cols = _table_columns(inspector, "products")
    if prod_cols:
        for col, ddl in [
            ("has_extended_warranty", "ALTER TABLE products ADD COLUMN has_extended_warranty BOOLEAN DEFAULT 0"),
            ("extended_warranty_provider", "ALTER TABLE products ADD COLUMN extended_warranty_provider VARCHAR(100) DEFAULT ''"),
            ("extended_warranty_contract_number", "ALTER TABLE products ADD COLUMN extended_warranty_contract_number VARCHAR(100) DEFAULT ''"),
            ("extended_warranty_duration_months", "ALTER TABLE products ADD COLUMN extended_warranty_duration_months INTEGER DEFAULT 0"),
        ]:
            if col not in prod_cols:
                statements.append(ddl)

    doc_cols = _table_columns(inspector, "documents")
    if doc_cols:
        for col, ddl in [
            ("doc_id", "ALTER TABLE documents ADD COLUMN doc_id VARCHAR(50)"),
            ("product_id", "ALTER TABLE documents ADD COLUMN product_id VARCHAR(50)"),
            ("user_id", "ALTER TABLE documents ADD COLUMN user_id VARCHAR(50)"),
            ("verified_at", "ALTER TABLE documents ADD COLUMN verified_at DATETIME"),
            ("verified_by", "ALTER TABLE documents ADD COLUMN verified_by VARCHAR(50)"),
        ]:
            if col not in doc_cols:
                statements.append(ddl)

    audit_cols = _table_columns(inspector, "audit_logs")
    if audit_cols:
        for col, ddl in [
            ("user_id", "ALTER TABLE audit_logs ADD COLUMN user_id VARCHAR(50)"),
            ("entity_type", "ALTER TABLE audit_logs ADD COLUMN entity_type VARCHAR(50)"),
            ("entity_id", "ALTER TABLE audit_logs ADD COLUMN entity_id VARCHAR(50)"),
        ]:
            if col not in audit_cols:
                statements.append(ddl)

    user_cols = _table_columns(inspector, "users")
    if user_cols:
        for col, ddl in [
            ("phone_number", "ALTER TABLE users ADD COLUMN phone_number VARCHAR(50) DEFAULT ''"),
            ("mailing_address", "ALTER TABLE users ADD COLUMN mailing_address TEXT DEFAULT ''"),
        ]:
            if col not in user_cols:
                statements.append(ddl)

    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                print(f"[migrate] skip {stmt}: {exc}", flush=True)

        inspector = inspect(engine)
        doc_cols = _table_columns(inspector, "documents")
        if doc_cols:
            claim_meta = doc_cols.get("claim_id") or {}
            if claim_meta.get("nullable") is False:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS documents_migrated (
                        id INTEGER PRIMARY KEY,
                        doc_id VARCHAR(50),
                        claim_id VARCHAR(50),
                        product_id VARCHAR(50),
                        user_id VARCHAR(50),
                        file_name VARCHAR(150) NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        file_path VARCHAR(255) NOT NULL,
                        file_hash VARCHAR(100) NOT NULL,
                        extracted_data_json TEXT,
                        verified_at DATETIME,
                        verified_by VARCHAR(50),
                        created_at DATETIME
                    )
                    """
                ))
                existing_new = [c["name"] for c in inspect(engine).get_columns("documents")]
                select_cols = [
                    "id",
                    "doc_id" if "doc_id" in existing_new else "NULL AS doc_id",
                    "claim_id",
                    "product_id" if "product_id" in existing_new else "NULL AS product_id",
                    "user_id" if "user_id" in existing_new else "NULL AS user_id",
                    "file_name",
                    "file_type",
                    "file_path",
                    "file_hash",
                    "extracted_data_json",
                    "verified_at" if "verified_at" in existing_new else "NULL AS verified_at",
                    "verified_by" if "verified_by" in existing_new else "NULL AS verified_by",
                    "created_at",
                ]
                conn.execute(text(
                    f"INSERT INTO documents_migrated (id, doc_id, claim_id, product_id, user_id, file_name, file_type, file_path, file_hash, extracted_data_json, verified_at, verified_by, created_at) "
                    f"SELECT {', '.join(select_cols)} FROM documents"
                ))
                conn.execute(text("DROP TABLE documents"))
                conn.execute(text("ALTER TABLE documents_migrated RENAME TO documents"))


def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    from assurex_claim_engine.db.status_history import backfill_claim_status_history

    backfill_claim_status_history()
    print("Database tables initialized successfully!")
    seed_users_and_samples()

def seed_users_and_samples():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            default_users = [
                User(user_id="USR-0001", email="customer@assurex.com", hashed_password=hash_password("customer123"), full_name="John Customer", role="customer"),
                User(user_id="USR-0002", email="service@assurex.com", hashed_password=hash_password("service123"), full_name="Authorized Service Desk", role="service_center"),
                User(user_id="USR-0003", email="reviewer@assurex.com", hashed_password=hash_password("reviewer123"), full_name="Sarah Adjudicator", role="reviewer"),
                User(user_id="USR-0004", email="admin@assurex.com", hashed_password=hash_password("admin123"), full_name="System Admin", role="admin")
            ]
            db.add_all(default_users)
            db.commit()
            print("Default seed users created!")
    finally:
        db.close()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
