# Database dictionary

Generated from the final SQLAlchemy declarations. SQLite demo data is synthetic.

## User

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| user_id | `Column(String(50), unique=True, index=True, nullable=False)` |
| email | `Column(String(100), unique=True, index=True, nullable=False)` |
| hashed_password | `Column(String(255), nullable=False)` |
| full_name | `Column(String(100), nullable=False)` |
| role | `Column(String(30), nullable=False, default='customer')` |
| phone_number | `Column(String(50), nullable=True, default='')` |
| mailing_address | `Column(Text, nullable=True, default='')` |
| created_at | `Column(DateTime, default=_utcnow)` |

## Product

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| product_id | `Column(String(50), unique=True, index=True, nullable=False)` |
| user_id | `Column(String(50), ForeignKey('users.user_id'), nullable=False)` |
| product_name | `Column(String(150), nullable=False)` |
| category | `Column(String(50), nullable=False)` |
| brand | `Column(String(50), nullable=False)` |
| model_number | `Column(String(50), nullable=False)` |
| serial_number | `Column(String(50), nullable=False)` |
| purchase_date | `Column(String(20), nullable=False)` |
| purchase_price | `Column(Float, nullable=False)` |
| retailer | `Column(String(100), nullable=False)` |
| warranty_duration_months | `Column(Integer, nullable=False, default=24)` |
| has_extended_warranty | `Column(Boolean, default=False)` |
| extended_warranty_provider | `Column(String(100), nullable=True)` |
| extended_warranty_contract_number | `Column(String(100), nullable=True)` |
| extended_warranty_duration_months | `Column(Integer, nullable=True, default=0)` |
| created_at | `Column(DateTime, default=_utcnow)` |

## Claim

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| claim_id | `Column(String(50), unique=True, index=True, nullable=False)` |
| user_id | `Column(String(50), ForeignKey('users.user_id'), nullable=False)` |
| product_id | `Column(String(50), ForeignKey('products.product_id'), nullable=False)` |
| fault_category | `Column(String(100), nullable=False)` |
| damage_type | `Column(String(100), default='none')` |
| fault_occurrence_date | `Column(String(20), nullable=False)` |
| claim_submission_date | `Column(String(20), nullable=False)` |
| description | `Column(Text, nullable=True)` |
| status | `Column(String(50), default='Submitted')` |
| python_predicted_class | `Column(String(50), nullable=True)` |
| python_top_confidence | `Column(Float, nullable=True)` |
| vision_predicted_class | `Column(String(50), nullable=True)` |
| vision_top_confidence | `Column(Float, nullable=True)` |
| confidence_difference | `Column(Float, nullable=True)` |
| consistency_status | `Column(String(50), nullable=True)` |
| final_decision | `Column(String(50), nullable=True)` |
| decision_explanation_json | `Column(Text, nullable=True)` |
| reviewer_comments | `Column(Text, nullable=True)` |
| reviewed_by | `Column(String(50), nullable=True)` |
| override_flag | `Column(Boolean, default=False)` |
| document_hash | `Column(String(100), nullable=True)` |
| extended_warranty_provider | `Column(String(100), nullable=True)` |
| extended_warranty_contract_number | `Column(String(100), nullable=True)` |
| model_version | `Column(String(20), nullable=True)` |
| created_at | `Column(DateTime, default=_utcnow)` |

## Document

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| doc_id | `Column(String(50), unique=True, index=True, nullable=True)` |
| claim_id | `Column(String(50), ForeignKey('claims.claim_id'), nullable=True)` |
| product_id | `Column(String(50), ForeignKey('products.product_id'), nullable=True)` |
| user_id | `Column(String(50), ForeignKey('users.user_id'), nullable=True)` |
| file_name | `Column(String(150), nullable=False)` |
| file_type | `Column(String(50), nullable=False)` |
| file_path | `Column(String(255), nullable=False)` |
| file_hash | `Column(String(100), nullable=False)` |
| extracted_data_json | `Column(Text, nullable=True)` |
| verified_at | `Column(DateTime, nullable=True)` |
| verified_by | `Column(String(50), nullable=True)` |
| created_at | `Column(DateTime, default=_utcnow)` |

## Repair

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| repair_id | `Column(String(50), unique=True, index=True, nullable=False)` |
| product_id | `Column(String(50), ForeignKey('products.product_id'), nullable=False)` |
| user_id | `Column(String(50), ForeignKey('users.user_id'), nullable=False)` |
| repair_date | `Column(String(20), nullable=False)` |
| service_center_name | `Column(String(150), nullable=False)` |
| replaced_parts | `Column(String(255), nullable=True)` |
| repair_cost | `Column(Float, nullable=True, default=0.0)` |
| outcome | `Column(String(100), nullable=True)` |
| authorized | `Column(Boolean, default=True)` |
| created_at | `Column(DateTime, default=_utcnow)` |

## AuditLog

| Field | ORM declaration |
|---|---|
| id | `Column(Integer, primary_key=True, index=True)` |
| claim_id | `Column(String(50), nullable=True)` |
| user_id | `Column(String(50), nullable=True)` |
| entity_type | `Column(String(50), nullable=True)` |
| entity_id | `Column(String(50), nullable=True)` |
| action | `Column(String(100), nullable=False)` |
| performed_by | `Column(String(50), nullable=False)` |
| details_json | `Column(Text, nullable=True)` |
| timestamp | `Column(DateTime, default=_utcnow)` |
