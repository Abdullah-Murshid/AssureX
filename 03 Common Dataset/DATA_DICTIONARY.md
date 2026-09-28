# Structured claim data dictionary

| Field | Type | Meaning |
|---|---|---|
| claim_id | string | Unique identifier assigned to each claim (e.g., CLM-2026-0001). |
| user_id | string | Unique identifier of claimant customer or service station. |
| product_id | string | Unique identifier of registered product under warranty. |
| product_name | string | Name of product model and brand. |
| product_category | string | Product warranty category. |
| brand | string | Manufacturer brand name. |
| model_number | string | Product model designation. |
| user_serial_number | string | Serial number provided by user. |
| ocr_serial_number | string | Serial number extracted via document OCR. |
| serial_match_status | string | Serial verification match status. |
| purchase_date | date | Date product was purchased. |
| purchase_price | float | Retail purchase price in USD. |
| retailer | string | Authorized merchant or store name. |
| warranty_duration_months | integer | Total warranty coverage period in months. |
| warranty_expiry_date | date | Calculated end date of warranty coverage. |
| fault_occurrence_date | date | Date fault symptom was observed. |
| claim_submission_date | date | Date claim was submitted to engine. |
| fault_category | string | Reported fault defect category. |
| damage_type | string | Excluded physical damage type if any. |
| previous_repairs_count | integer | Number of previous repair logs for this product. |
| has_unauthorized_repairs | boolean | Flag indicating unauthorized service attempts. |
| has_receipt | boolean | True if receipt invoice document attached. |
| has_warranty_card | boolean | True if warranty card attached. |
| has_product_photo | boolean | True if product damage photo attached. |
| has_serial_photo | boolean | True if serial number photo attached. |
| missing_documents_count | integer | Total count of missing mandatory documents. |
| contradiction_flag | boolean | True if timeline contradiction detected. |
| duplicate_claim_flag | boolean | True if duplicate serial/hash detected. |
| product_age_days | integer | Derived days between purchase and submission. |
| remaining_warranty_days | integer | Derived days remaining in warranty coverage. |
| reporting_delay_days | integer | Derived days between fault occurrence and submission. |
| actual_class | string | Ground truth adjudication label. |
