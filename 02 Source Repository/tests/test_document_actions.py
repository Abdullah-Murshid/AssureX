"""
Test Document Vault delete and replace functionality (Module xiv)
using direct DB and file operations.
"""

import os
import io
import json
from datetime import datetime, timezone
from assurex_claim_engine.db.database import init_db, SessionLocal, Document, User
from assurex_claim_engine.ocr.parser import DocumentOCRParser


def test_document_replace_and_delete_unit():
    init_db()
    db = SessionLocal()
    parser = DocumentOCRParser()

    doc_id = "DOC-TEST-9999"
    test_path = os.path.join("uploads", f"{doc_id}_orig.txt")
    os.makedirs("uploads", exist_ok=True)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("Initial document content for unit test")

    doc = Document(
        doc_id=doc_id,
        user_id="USR-ADMIN-001",
        file_name="orig.txt",
        file_type="purchase_receipt",
        file_path=test_path,
        file_hash=parser.compute_file_hash(b"Initial document content for unit test"),
    )
    db.add(doc)
    db.commit()

    # 1. Verify existence
    fetched = db.query(Document).filter(Document.doc_id == doc_id).first()
    assert fetched is not None
    assert os.path.exists(test_path)

    # 2. Simulate Replace: new file written, old file removed, hash updated
    new_path = os.path.join("uploads", f"{doc_id}_replaced.txt")
    with open(new_path, "w", encoding="utf-8") as f:
        f.write("Replaced new document content")

    if os.path.exists(fetched.file_path):
        os.remove(fetched.file_path)

    fetched.file_name = "replaced.txt"
    fetched.file_path = new_path
    fetched.file_hash = parser.compute_file_hash(b"Replaced new document content")
    db.commit()

    assert not os.path.exists(test_path)
    assert os.path.exists(new_path)
    assert fetched.file_name == "replaced.txt"

    # 3. Simulate Delete: remove file from disk and record from DB
    if os.path.exists(fetched.file_path):
        os.remove(fetched.file_path)
    db.delete(fetched)
    db.commit()

    assert not os.path.exists(new_path)
    assert db.query(Document).filter(Document.doc_id == doc_id).first() is None
    db.close()
