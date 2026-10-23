# AssureX Claim Engine — SRS Compliance Audit

**Compared against:** *AssureX Claim Engine — Software Requirements Specification, Version 1.0* (Aptech Ltd., 37 pp., in `AssureX Claim Engine-NextWave AI and ML_SRS.pdf`)
**Audited package:** `AssureX_Final_Submission/` (16 deliverable folders + `02 Source Repository`)
**Audit date:** 2026-10-22
**Method:** source and document inspection, live HTTP probe, artifact inspection, independent re-scoring of the shipped models, dataset rule reproduction, and public-URL verification. Commands and raw results are in §11.

> **Post-audit update (2026-10-22):** TensorFlow was installed after the first pass, and the GTM path now runs. P0-1 is **resolved in the working tree**. The card pipeline was rebuilt as **v4 status tiles** (600×600, renderer parity, 2,550 cards — §16). The v4 GTM export scores **78.22% test / 86.67% live** — live passes, test is still below 85% because Valid recall is 34.7% (§17). P0-2, P0-3, and P0-4 remain.

---

## 1. Verdict

**The submission is not SRS-compliant as delivered.** The codebase is broad and the documentation is unusually candid, but four hard failures prevent acceptance:

| # | Blocker | SRS reference | Evidence |
|---|---|---|---|
| **P0-1** | **Claim evaluation was impossible in the shipped environment** (TensorFlow absent, GTM never loaded, submission returned HTTP 503). **Resolved in the working tree on 2026-10-22** by installing `tensorflow==2.21.0` + `tf-keras==2.21.0`, routing `tf.keras` through the legacy bridge, and adding both to `requirements.txt` (§13). | 1.6 x, xxi, xxxiv; 1.10.10 | As delivered: `/health` → `gtm_model_ready:false`; submit → `503` after 15.1 s. After fix: `/health` → `models_ready:true`; submit → `200` in **5.1 s** with both model results persisted |
| **P0-2** | **The GTM model misses the mandatory test-accuracy floor.** The original export scored 36.89% (v1) / 33.3% (v3) with all-Invalid predictions. The **v4 export (hash `b69ad289…`, 18:16) scores 78.22% on the v4 test set (176/225) and 86.67% live (26/30)**. Invalid and Manual Review recall are both 100%; **Valid recall is 34.7%** (26/75), so the test gate still fails. | 1.7.4 | `05 .../v4_evaluation.json`; `05 .../METRICS.md`; `06 .../evaluation_run.json`; §16–§17 |
| **P0-3** | **The public GitHub repository has one commit, by one contributor.** The SRS requires meaningful commits across all five competition days and commits from all team members. | 1.8.2; 1.10.11 | GitHub API: `commits` returns 1 root commit (2026-09-28); `contributors` returns 1 contributor |
| **P0-4** | **The test evidence is not reproducible from the package and is internally inconsistent.** The shipped venv has no `pytest`; `starlette 1.9` requires `httpx2` while `requirements.txt` pins `httpx`; recorded pytest logs come from another machine and a different scikit-learn version (1.7.2 vs 1.9.1 artifacts). Results are quoted as 42, 35, and 39 checks in different documents. | 1.10.8; 1.10.4 | `08 .../pytest_results.txt`; `AUTOMATED_RESULTS.txt`; `TEAM_VERIFICATION.csv`; `README.md` |

A fifth issue is methodological rather than an outright SRS violation: **the tabular label is 100% reproducible from six features**, and the shipped tabular model/report were **not produced from the shipped CSVs**. The 91.56% number is real on the supplied test set, but the task is largely rule memorisation, and the historical 92% report belongs to a dataset (`data/v2`) that is absent and cannot be regenerated.

### Scorecard

| Area | Implemented | Partial | Broken / absent |
|---|---:|---:|---:|
| Functional requirements (50) | **23** | **25** | **2** |
| Non-functional requirements (5) | 0 | 3 (unverified) | 2 |
| Deliverables (16) | **3** | **11** | **2** |
| Anti-shortcut / integrity (10) | 2 | 3 | 2 (5 unverifiable) |

> “Implemented” means the behaviour exists in code and is exercised at least at unit/route level. As delivered, P0-1 blocked the end-to-end submission path; after the §13 runtime fix, a claim reaches the dossier with both models.

---

## 2. What is genuinely strong

These should be preserved, not rewritten:

- **Architecture and separation of concerns.** `web/` (routes), `db/` (ORM), `decision/` (comparison, fusion, contradictions, derived features), `rule_engine/` (policy registry), `ocr/`, `models/`, `reporting/`, `dataset_generator/` are cleanly separated and mostly readable.
- **Dual-model comparison and fusion logic.** All five SRS consistency states are implemented with configurable thresholds (`Strong Match`, `Acceptable Match`, `Weak Match`, `Model Disagreement`, `Uncertain Result`), and the confidence difference formula is exactly the SRS formula (`decision/comparison.py:44-68`).
- **Configurable policy engine.** Three category JSON files plus a registry of rule handlers; hard-fail / warning / manual-review groups; admin editor reloads policies without a restart (`rule_engine/evaluator.py`, `web/app.py:1015-1167`).
- **Dataset structure.** 1,500 records, exactly 500/500/500, stratified 1,050/225/225, **zero Claim-ID overlap between splits**, 2,550 cards with **all 2,550 mapping paths resolving on disk** and **zero class/split-folder mismatches** in `03 Common Dataset`. This part is well done.
- **Audit trail and reviewer workflow.** Real audit records for registration, upload, OCR correction, inference, status changes, overrides, policy edits; reviewer override preserves the original AI result and requires comments (`web/app.py:2030-2066`).
- **Documentation honesty.** The project report, blog, and audit notes openly state the GTM failure and the incomplete provenance. This is rare and should not be hidden.

---

## 3. Functional requirements (SRS §1.6, i–l)

Legend: **✅** implemented · **🟡** partial · **🔴** broken/absent.

| # | Requirement | Status | Evidence / gap |
|---|---|:--:|---|
| i | Registration & authentication / RBAC | ✅ | Session auth, PBKDF2, four roles, route guards, 403 page. Public registration cannot create admin. |
| ii | Profile management | ✅ | Name/email/phone/address edit + password change; unique `user_id`. |
| iii | Product registration | ✅ | All requested fields incl. extended warranty; unique `PRD-*`; negative price/duration rejected. Date format not server-validated. |
| iv | Warranty record management | 🟡 | Warranty is computed from product fields + category policy; no per-warranty entity, coverage conditions, exclusions, or service-centre record. Extended provider/contract stored on product. |
| v | Receipt / invoice upload | ✅ | PDF/JPG/JPEG/PNG, 10 MB cap, authenticated access, path traversal guard. |
| vi | Receipt scanning & extraction | 🟡 | Embedded PDF text + regex extracts date, invoice, serial, retailer, model, product, amount, warranty. EasyOCR is not installed, so image/scanned-PDF receipts extract nothing. OCR “confidence” is hard-coded 0.95/0.88. |
| vii | Extracted-data verification | 🟡 | Full correction form exists in the document vault; corrections are audited. Not surfaced in the claim flow; corrected invoice/amount are not written back to the claim/product. |
| viii | Warranty tracking | ✅ | Start/expiry/remaining computed; Active / Expiring Soon / Grace / Expired / Extended Warranty statuses. Fixed 30-day months. |
| ix | Warranty expiry alerts + configurable lead time | ✅ | In-app banner + alerts tabs; admin can set `warranty_alert_days` (1–180) and it is persisted to `settings.yaml`. |
| x | Claim registration | 🟡 | Unique `CLM-2026-*`, draft/submit, links user/product/documents. **Full submission is blocked by P0-1**; IDs are not concurrency-safe. |
| xi | Claim information collection | 🟡 | Fault category/date, damage, description, purchase and warranty come from the product. No claim amount, service-history input, or previous-replacement fields on the form; `previous_repairs_count`/`has_unauthorized_repairs` are backend-only parameters with no inputs. |
| xii | Fault & damage evidence upload | 🟡 | Receipt, warranty card, product photo, serial photo, damage photo. No fault-video or diagnostic/repair-report upload in claim intake or vault UI (file-type map supports them, UI does not). |
| xiii | Repair history management | ✅ | Repair date, centre, parts, cost, outcome, authorized flag; feeds rule evaluation and review. |
| xiv | Document organisation | ✅ | Vault by product/claim with view, download, replace, delete, verify; ownership checks on `/uploads/`. |
| xv | Data validation | 🟡 | File type/size and some numeric checks; duplicate IDs generated safely. Only `fault_category` is HTML-required. Free-text dates are accepted; invalid dates silently fall back to defaults in `derived_features.py:89-95` instead of producing a validation error. |
| xvi | Data pre-processing | ✅ | Shared derived-feature module used by dataset, offline evaluation, and live inference; scaler/encoder in the saved pipeline. |
| xvii | Common warranty claim dataset | ✅ | 1,500 records / 500 each; 1,050/225/225; 2,100 train + 225 val + 225 test cards; same Claim IDs. Packaged in `03`, not under `02 Source Repository/data`. |
| xviii | Python classification model | ✅ | XGBoost selected after RF + Logistic Regression + XGBoost comparison; 5-fold CV, validation-based selection, saved artifacts. |
| xix | Python confidence scores | ✅ | Three class probabilities returned and rendered as bars in the dossier. |
| xx | Claim Summary Card generation | ✅ | 840×500 PNG from claim facts only; no prediction/confidence/final decision in pixels; two training variations. |
| xxi | Google Teachable Machine classification | 🔴 | Integration code is correct (H5, labels, 224×224, `/127.5-1`), but TensorFlow is absent → model unavailable. When evaluated, accuracy is 36.89% and live cards are 30/30 “Manual Review”. |
| xxii | Model prediction comparison | ✅ | Stores both classes, `classes_match`, and displays consistency status + both predictions. |
| xxiii | Confidence score comparison | ✅ | Absolute top-class difference calculated and displayed; exact SRS formula. |
| xxiv | Model consistency status | ✅ | All five states, configurable thresholds in `config/settings.yaml`. |
| xxv | Warranty rule validation | 🟡 | Expiry, exclusions, unauthorized repair, late reporting, serial mismatch, missing docs, repair frequency, commercial use, custom wiring. No replacement rule; category-specific coverage conditions are thin. |
| xxvi | Configurable warranty policies | 🟡 | Three JSON policies, admin editor, per-category selection. Missing explicit `warranty_start_conditions`, `repair_conditions`, `replacement_conditions` — the package’s own `POLICY_FIELD_MATRIX.csv` marks these “Team definition needed”. |
| xxvii | Serial-number verification | 🟡 | Compares entered serial with OCR receipt serial only. Does not compare warranty card, product image, or repair records; absent OCR falls back to the entered serial. |
| xxviii | Contradiction detection | 🟡 | Fault before purchase, claim before fault, user-vs-OCR serial. No inconsistent model numbers or multi-document serial conflicts. |
| xxix | Missing document detection | ✅ | Policy `mandatory_documents` checked, named in the UI/route, routes to manual review. Caveat: presence is product-wide, not claim-specific. |
| xxx | Duplicate claim detection | 🟡 | Document hash + serial/invoice + explicit flag. **Invoice is never stored on the claim**, so the serial+invoice path can never fire; no claimant/fault-description similarity. |
| xxxi | Document duplicate detection | ✅ | SHA-256 on every upload, duplicate warning, audit detail. |
| xxxii | AI-generated claim summary | ✅ | Narrative generator composes product, evidence, warranty, model, rule, and outcome sentences; shown in dossier. |
| xxxiii | Claim preparation assistance | 🟡 | `/claims/pre-check` returns missing documents, warnings, contradictions, actions. The UI prints “Ready: undefined” without a product and discards the server’s contradictions/warranty/serial fields; new-product users cannot pre-check. |
| xxxiv | Final claim decision | 🟡 | Fusion produces the three required outcomes from both models, rules, docs, duplicates, contradictions. **Cannot execute end-to-end in the shipped environment** (P0-1); with live GTM output it would route essentially everything to Manual Review. |
| xxxv | Decision explanation | 🟡 | Supporting/opposing factors, passed/failed rules, required actions are stored. The dossier omits structured contradictions, duplicates, missing-document list, and required actions; printable report has related gaps. |
| xxxvi | Manual review workflow | ✅ | Queue for `Manual Review` / `Request More Info`; reviewer can Approve, Reject, Request More Info, Close; comments required. |
| xxxvii | Reviewer comments & override | ✅ | Comments, reviewer identity, override flag, original AI decision retained, audit entry. |
| xxxviii | Claim status tracking | 🟡 | Eight stages defined, but `Submitted` and `Under Evaluation` are never assigned; a claim jumps Draft → Approved/Rejected/Manual Review. No transition history; stepper `.done` state is never applied. |
| xxxix | Notification & alerts | 🟡 | Warranty-expiry banner and alerts page. No persisted notification for claim submission, missing documents, status change, review completion, approval, or rejection. |
| xl | Claim dashboard | 🟡 | Totals, pending actions, products, recent claims, filters. Missing active/expiring warranty counts, saved receipts, and a pending-action metric. |
| xli | Administrator dashboard | 🟡 | Totals, valid/invalid/manual counts, disagreements, one stacked chart. Missing pending, duplicate alerts, average confidence, trends, model performance; the manual-review count is computed but **never rendered**. |
| xlii | Search & filtering | 🟡 | Products: serial/category/status. Dashboard: claim/product/status/serial. Review queue filters are **decorative** (route ignores them). No risk level, confidence range, reviewer, or date-range filter; warranties and analytics have none. |
| xliii | Data analysis & reporting | 🟡 | Basic outcome counts and one chart. No frequently reported faults, rejection reasons, category/repair patterns, model performance, or manual-review frequency analysis. |
| xliv | Downloadable claim report | 🟡 | PDF + print + download. Omits contradictions/duplicates/missing docs/audit; prints `$0.00` claim amount (no such column); review date always blank; mislabels every non-`Consistent` result as divergence. |
| xlv | Data export | 🟡 | CSV of claims only, no selection UI; no product/warranty/analytics export; CSV is Excel-compatible. |
| xlvi | Data storage | ✅ | SQLite via SQLAlchemy; users, products, claims, documents, repairs, audit. No notification table and no separate prediction-history table, but results are persisted in the claim/dossier JSON. |
| xlvii | Audit trail | ✅ | Broad action coverage and an audit page; `details_json` is stored but not rendered. |
| xlviii | Model version tracking | 🟡 | A single `model_version` label (`v2`) per claim; no GTM version/hash, no policy version, no per-artifact link. Historic results are immutable, which is good. |
| xlix | Error handling | 🟡 | Friendly flash messages and 403/404 pages. The global handler can surface `str(exc)` to the user (`app.py:208`), and the 503 says “Models still loading” when the real cause is missing TensorFlow. |
| l | Monitoring & anomaly alerts | 🔴 | `monitoring_flags()` exists but is never called. No alerts for failed uploads, repeated logins, model failures, low confidence, or excessive disagreement. |

**Counts: 23 ✅, 25 🟡, 2 🔴.**

---

## 4. Non-functional requirements (SRS §1.7)

| # | Requirement | Verdict | Assessment |
|---|---|:--:|---|
| 1 | ≤ 5 s end-to-end under normal conditions | 🟡 unverified | No timing benchmark. Offline pair inference is fast (~0.55 s/claim across 225 claims), but OCR has a 3.5 s timeout and TF model load is heavy. The live path currently returns 503, so the target cannot be demonstrated. |
| 2 | 10,000 claims, multiple tenants, concurrent users | 🟡 unverified | SQLite, no load test, no concurrency test. `analytics` loads **all** claims (unpaginated); ID generation is race-prone. |
| 3 | Usable / intuitive desktop-tablet-mobile UI | 🟡 | Responsive CSS, mobile sidebar, tables scroll. Broken/dead controls (reviewer filters, 403 links shown to reviewers, `import_csv` fake progress bar) reduce usability. |
| 4 | Both models ≥ 85% on unseen test claims | 🔴 **fail** | Python 91.56% numerically passes; **GTM 36.89%** fails badly (0% Valid recall). SRS requires both. |
| 5 | ≥ 99% availability in business hours | 🔴 unverified | No deployment URL; local-only demonstration is SRS-permitted, but uptime was not measured and the app is not operationally ready. |

---

## 5. Deliverables (SRS §1.10, 1–16)

| # | Deliverable | Status | Notes |
|---|---|:--:|---|
| 1 | Project report | 🟡 | Comprehensive MD + DOCX, all required diagrams, DB dictionary. Inconsistent test counts (35 vs 42), references a `PROJECT_REPORT.pdf` that is not present, and repeats the GTM failure. |
| 2 | Source code | 🟡 | Complete app; `data/summary_cards` empty; `requirements.txt` omits TensorFlow; dead modules; training entry point points at absent `data/v2`. |
| 3 | Dataset | ✅ | 1,500 records, 2,550 cards, mapping/dictionary/statistics/generators; all 2,550 mapping paths resolve. Caveat: deterministic labels (§8). |
| 4 | Python model evidence | 🟡 | Model, metrics, predictions, misclassified samples, notebooks. Notebooks are **empty shells**; report/model do not match shipped CSVs; preprocessing was fitted before CV. |
| 5 | GTM evidence | 🔴 | Only H5/labels/metrics/predictions. Missing project link/screenshots, class samples, training configuration, images per class, training observations, retraining details, model version, test screenshots. |
| 6 | Model comparison report | 🟡 | 30 paired cases with all six probabilities, gap, consistency, rules, docs, contradictions, duplicates, decision. No overall narrative summary; GTM result is 36.89%. |
| 7 | Warranty policy files | 🟡 | Three JSON policies + field matrix + completion templates. Runtime policies still lack start/repair/replacement conditions. |
| 8 | Test cases & results | 🟡 | Plan, pytest log, 39-check HTTP smoke, 11 scenario definitions. `MANDATORY_SCENARIOS.csv` Actual columns are `[[SCENARIO_ACTUAL_RESULTS]]` placeholders; category coverage is `[[TEAM_TEST_RESULTS]]` placeholders; counts conflict. |
| 9 | Installation instructions | 🟡 | Many `[[...]]` placeholders (`SUPPORTED_OS`, `RELEASE_RUNTIME`, `CLEAN_INSTALL_LOG`); no certified clean install; TensorFlow split into a separate 3.11 environment. |
| 10 | Execution instructions | 🟡 | Accurate baseline walkthrough, but `[[WARRANTY_WORKFLOW]]`, `[[FINAL_WORKFLOW_NOTES]]`, `[[RELEASE_COMMIT]]` remain blank. |
| 11 | GitHub repository | 🔴 | Public URL resolves, but **1 commit / 1 contributor**; three commit screenshots for five members; no five-day history. README inside the repo links two non-existent files. |
| 12 | Deployment | 🟡 | No public URL (local alternative is SRS-permitted). Health example says `{"status":"healthy","version":"2.0.0"}`; actual is `loading` and app version is 1.0.0. No Dockerfile, only a snippet. |
| 13 | Demonstration video | ✅ | `demo_video.mp4`, 203.3 MB, **21.7 min**, 29-scene coverage sheet. Content not independently verified here. |
| 14 | Technical blog | ✅ | Published URL returns HTTP 200; 2,974 words; covers architecture, dataset, models, rules, limitations. |
| 15 | AI usage declaration | 🟡 | Exists, but “Verified & Signed Off” rows assert work the same package describes as pending; tool prompts and per-member verification are thin. |
| 16 | Final submission checklist | 🟡 | SRS PDF + 332-row matrix. Only **17** rows say “Included in snapshot”; **214** say “final build review required” — the package itself acknowledges it is unfinished. |

**Counts: 3 ✅, 11 🟡, 2 🔴.**

---

## 6. Competition integrity / anti-shortcut (SRS §1.8)

| # | Requirement | Status | Evidence |
|---|---|:--:|---|
| 1 | Each member explains their modules | Unverifiable | No per-member walkthrough evidence. |
| 2 | Meaningful commits across all five days | 🔴 **fail** | GitHub API: one parentless commit, 2026-09-28; repo created 2026-09-27; one contributor. |
| 3 | Development log (work, problems, failures, changes, tests) | 🔴 **absent** | No dev-log file anywhere in the package. |
| 4 | Evaluators may ask to explain any function | Unverifiable | Code is generally readable; dead/duplicated modules increase risk. |
| 5 | Surprise modification (exclusion, threshold, date format, rule, decision, filter) | 🟡 | Thresholds and policies are editable without code changes; date formats are **not** pluggable (hard-coded `%Y-%m-%d`), and adding a filter would require route work. |
| 6 | Fix a deliberately introduced defect | Unverifiable | — |
| 7 | No unused code, unexplained code, hard-coded answers | 🔴 **risk** | `web/services.py` (298 lines) is entirely unused; `models/image_classifier_v2.py` (Torch) is unusable and unreferenced; `monitoring_flags` / `apply_claim_filters` are dead; hard-coded alert date `2026-09-27`; hard-coded `file:///c:/Users/hp/...` in the CSV import page; hard-coded OCR confidence constants. |
| 8 | Hidden claims, no lookup tables | 🟡 | Live inference, no lookup. But the tabular model uses `duplicate_claim_flag`, which is always `False` at runtime (train/serve skew), and the dataset label is deterministic from six inputs. |
| 9 | Declare AI tools in `AI_USAGE.md` | ✅ | Present with tool, purpose, affected files, testing caveats. Per-member prompt/verification detail is thin. |
| 10 | AI output cannot replace understanding | Unverifiable | Five “signed off” rows exist, but the package’s own evidence contradicts several of the claims. |

---

## 7. Model and dataset findings (verified independently)

### 7.1 Python model

- **Shipped model:** `XGBClassifier` (90 trees, depth 4, lr 0.07), 75 transformed features, classes `[Invalid, Manual Review, Valid]`.
- **Re-scored on shipped `data/test.csv`: 91.56%** — confusion matrix `[[75,0,0],[0,70,5],[13,1,61]]`. This matches `04 .../current_test_evaluation.json` and `06 .../evaluation_run.json`.
- **But the historical `model/v2/tabular_evaluation_report.json` reports 92.0%** with a different confusion matrix (`[[65,10,0],[0,70,5],[3,0,72]]`) and different per-class metrics. The shipped model scores **90.67% on `data/train.csv`** — lower than on test — so it demonstrably **did not train on the shipped train split**.
- The preprocessor’s `feature_names_in_` includes `actual_class`, proving the training call passed the label column into the pipeline (dropped by `remainder='drop'`, so not used, but indicative of sloppy training plumbing).
- **V2 is not reproducible:** both v2 scripts target `data/v2`, which does not exist; `generate_dataset_v2.py:261` references an undefined `missing_docs_count` and raises `NameError`; the documented `tabular_model_v2.py` entry point therefore raises `FileNotFoundError`.
- Notebooks are placeholders: 4 cells / 2 cells, **zero outputs**.

**Conclusion:** the Python accuracy number passes the threshold on the supplied test set, but the training provenance required by SRS deliverables 4 and 6 is missing, and the historical report cannot be tied to the shipped artifacts.

### 7.2 GTM model

- Valid HDF5/Keras MobileNetV2, input `(None,224,224,3)`, output `(None,3)`, labels `0 Valid / 1 Invalid / 2 Manual`.
- **Not loadable** in the shipped environment: TensorFlow, Keras, h5py, and torch are absent; `requirements.txt` does not list TensorFlow.
- **Accuracy 36.89%** on 225 supplied test cards; **Valid Claim recall 0/75**; 211/225 predictions are “Invalid”.
- **Live-renderer check:** 30/30 cards → “Manual Review”, 14/30 correct (46.7%). This is the card renderer the application actually uses at submission. The model is highly sensitive to rendering/layout, which indicates it learned rendering artefacts or was trained on a different card distribution.
- Consequence: even with TensorFlow installed, fusion would see `Manual Review` vs the Python class and route virtually every claim to manual review. The dual-model automation would be degenerate.

### 7.3 Dataset

- **Split integrity is good:** 1,050/225/225, 350/75/75 per class, zero ID overlap, zero duplicate rows, zero nulls, internally consistent derived dates.
- **Cards are present in the dataset deliverable:** 2,550 files, 700/700/700 train, 75/75/75 val/test, all mapping paths resolve, zero class/split mismatches. (The **source repo’s** `data/summary_cards` is empty — a packaging inconsistency, not a missing dataset.)
- **Renderer mismatch (critical):** every packaged card is **750×520** with a footer and an older layout; the current `render_claim_card()` and the live app produce **840×500** with no footer. Neither shipped card script emits 750×520, so the packaged set cannot be regenerated from the shipped generator. The packaged cards also show overlapping/clipped values (long product names, warranty text, right-column values). This is a direct domain shift: GTM trains and is evaluated on 750×520 cards, then receives 840×500 cards at inference. It explains the **30/30 “Manual Review”** live result and is the first thing to fix before retraining.
- **Critical methodological issue:** a six-condition rule reproduces **1,500/1,500 labels**:

  ```text
  damage != none or unauthorized repair        -> Invalid
  contradiction or duplicate or serial mismatch
    or missing_documents_count > 0             -> Manual Review
  remaining_warranty_days < 0                  -> Invalid
  otherwise                                    -> Valid
  ```

  The task is therefore deterministic rule learning, not adjudication. Every contradiction/missing-doc/serial-mismatch row is Manual Review; every excluded-damage/unauthorized-repair row is Invalid. The reported 92% mostly measures reproduction of the generator’s `if/elif` chain.
- **Degenerate fields:** `has_warranty_card` and `has_product_photo` are `True` for all 1,500 rows; `serial_match_status` is only `Exact`/`Mismatch`; the 14 `duplicate_claim_flag` rows have no actual duplicate serial/hash evidence; one “Mismatch” row has identical serials.
- **Not documented:** `warranty_start_date` is in the CSVs but absent from `data_dictionary.json` (32 vs 33 columns).

---

## 8. Additional correctness and quality defects

These are not all SRS violations, but they will surface in a live evaluation:

1. **Claim submission is all-or-nothing on GTM.** `app.py:1685` calls the vision classifier unguarded; with TF missing, the broad `except` rolls back the claim and flashes an internal error. There is no deterministic/fallback mode even though the SRS requires the decision to consider both models.
2. **Evidence completeness is product-wide, not claim-specific.** `present_keys` queries all documents for the product (`app.py:1641-1643`), so a receipt uploaded for an earlier claim makes a later claim look complete. This weakens FR xxix and the “missing documents” decision.
3. **Invoice duplicate detection can never fire.** OCR extracts `invoice_number`, but no `invoice_number` is stored on `Claim` or passed into the claim dict; `contradiction.py` reads a key that is always absent.
4. **Invalid dates silently become favourable defaults.** `derived_features.py:89-95` catches any parse error and substitutes `product_age_days=100`, `remaining_warranty_days=200`, `reporting_delay_days=5`. A malformed hidden claim can look valid instead of being rejected — this is a direct hidden-test risk.
5. **Dossier hides the evidence it computed.** Contradictions, duplicate indicators, missing-document list, and required actions are in `decision_explanation_json` but not rendered in `dossier.html`; the printable report has the same gap plus a `$0.00` claim amount, blank review date, and a false “divergence” label for every non-`Consistent` status.
6. **Reviewer queue filters are non-functional.** `reviewer_queue()` never reads `claim_id`/`product_id`; the template renders inputs that do nothing.
7. **Dead/duplicated code.** `web/services.py` duplicates helpers and is never imported; `models/image_classifier_v2.py` is a Torch path with no artifact; `monitoring_flags()` and `apply_claim_filters()` are never called. Under SRS 1.8.7 this is a judging risk.
8. **Hard-coded values.** Alert suppression uses `Claim.created_at >= "2026-09-27"` (`helpers.py:176-180, 221-226`); the CSV import page hard-codes a developer `file:///c:/Users/hp/...` path; OCR confidence is a constant.
9. **Environment specification contradicts itself.** `pyproject.toml` requires `>=3.11,<3.12`; README says 3.11+; installation mentions a 3.14 web runtime and a separate 3.11/TF runtime; the shipped venv is 3.12.14.
10. **Test dependency mismatch.** `starlette 1.9` requires `httpx2`; `requirements.txt` pins `httpx>=0.24`. A clean install will still fail `TestClient` until this is pinned correctly.
11. **Version inconsistency.** App/`FastAPI` title says 1.0.0, package README and deployment record say 2.0.0, `pyproject.toml` says 2.0.1.
12. **Public repository gap.** The root has no `LICENSE`; `02 Source Repository/LICENSE` is not a licence (“No open-source license has been granted”). The repo README links `PROJECT_REQUIREMENTS_AND_ROADMAP.md` and `reports/model_comparison_report.md`, neither of which exists.

---

## 9. Requirement coverage by SRS section

| SRS section | Coverage | Comment |
|---|---|---|
| 1.1 Background / 1.2 Proposed solution | ✅ | Correctly reflected in report, blog, and architecture. |
| 1.3 Purpose / 1.4 Scope / 1.5 Constraints | ✅ | Documented; scope exclusions respected. |
| 1.6 Functional requirements | 🟡 **23/50 full, 25 partial, 2 broken** | Broad coverage; gaps concentrated in analytics, notifications, filtering, model versioning, monitoring, and the GTM path. |
| 1.7 Non-functional requirements | 🔴 | Accuracy fails for GTM; performance, scale, availability unverified. |
| 1.8 Integrity / anti-shortcut | 🔴 | GitHub history and dev log fail; dead/hard-coded code risk. |
| 1.9 Interface requirements | ✅ | FastAPI/Jinja/HTML/CSS/JS, SQLite, scikit-learn/XGBoost, PyMuPDF; TensorFlow not installed. |
| 1.10 Deliverables | 🟡 **3 complete, 11 partial, 2 broken** | Strong report/dataset/video/blog; thin GTM evidence, test evidence, installation/execution docs, GitHub history. |

---

## 10. Prioritised remediation plan

### P0 — must fix before any demonstration or submission

1. **Make the dual-model path runnable.**
   - Add `tensorflow-cpu==2.15.1` (Python 3.11) and compatible `numpy`/`h5py` to a single tested environment, or ship a launcher that creates/activates the 3.11 environment.
   - Add a startup readiness check that reports *why* GTM is unavailable, not “loading”.
   - Add a regression test that posts a real claim and asserts `200`/redirect and persisted probabilities from **both** models.
   - Acceptance: `/health` returns `models_ready:true`, `gtm_model_ready:true`; a live claim reaches the dossier with three GTM probabilities.

2. **Replace or retrain the GTM model until it meets ≥85%.**
   - Diagnose the live-renderer mismatch first (the 30/30 Manual Review result is the strongest clue).
   - Retrain on the exact renderer used by the app, with both variations, and evaluate on held-out **live-rendered** cards.
   - Do not tune on the test set; freeze a new unseen set.
   - Acceptance: ≥85% overall and ≥70% Manual Review recall on ≥30 unseen live-rendered cards, with a saved evaluation report.

3. **Fix the public GitHub history.**
   - The current repo is a single 2026-09-28 commit by one member; this directly contradicts SRS 1.8.2 and 1.10.11.
   - Add real incremental commits from each member for the remaining work (setup, dataset, model, web, tests, docs), with meaningful messages.
   - If the five competition days are already past, document the actual timeline honestly and add the missing members as commit authors where possible.
   - Acceptance: `contributors` shows all five members; `commits` spans the competition days with substantive diffs.

4. **Make the test evidence reproducible and consistent.**
   - Pin `pytest` and the correct HTTP test dependency (`httpx2` for Starlette 1.9, or pin Starlette to a version compatible with `httpx`).
   - Regenerate `pytest_results.txt` in the shipped environment, with the command, Python version, and dependency lock.
   - Reconcile the 42/35/39 counts; keep one canonical result.
   - Fill `MANDATORY_SCENARIOS.csv` Actual/Evidence/Tester/Date columns from real executions.

### P1 — required for credible SRS coverage

5. **Close the model/data provenance gap.** Ship `data/v2` or retrain the tabular model from the shipped CSVs and regenerate `tabular_evaluation_report.json` from the shipped artifacts. Fix `generate_dataset_v2.py`’s `missing_docs_count` NameError and the `data/v2` paths. Remove `actual_class` from the preprocessing fit frame.
6. **Address label determinism.** Add genuinely ambiguous/borderline records where class is not a function of six fields, or explicitly document that the dataset is rule-generated and the models are rule-recovery baselines. The SRS asks for normal, incomplete, contradictory, complex, and borderline scenarios; the current set is mostly deterministic.
7. **Render the decision evidence.** Add contradictions, duplicate reasons, missing-document list, required actions, claim facts, and audit history to `dossier.html` and the printable/PDF report; fix the `$0.00` amount, review date, and divergence-label bugs.
8. **Make evidence claim-specific.** Associate mandatory documents with the claim (or snapshot the set at submission), not just the product. Store `invoice_number` on the claim and use it in duplicate detection.
9. **Validate dates server-side.** Reject malformed dates with a user-facing error; remove the silent favourable defaults in `derived_features.py`.
10. **Complete the policy schema.** Add and enforce `warranty_start_conditions`, `repair_conditions`, and `replacement_conditions` in the three JSON policies.
11. **Complete the GTM evidence folder.** Project link/screenshots, class samples, training configuration, images per class, observations, retraining history, model version, test screenshots.
12. **Complete installation/execution docs.** Replace every `[[...]]` placeholder; record a clean install and a live claim; reconcile the Python/TF versions; fix the `run_app.bat` dependency check (it only checks fastapi/sqlalchemy/xgboost).
13. **Implement notifications and monitoring.** A notification record for submission/status/missing docs/review completion; wire `monitoring_flags()` into the admin dashboard; alert on failed uploads, repeated logins, model failures, low confidence, and disagreement spikes.
14. **Fix search/filter and analytics.** Wire reviewer-queue filters; add risk/confidence/reviewer/date filters; add pending/duplicates/average-confidence/trends/fault/rejection breakdowns; paginate analytics.
15. **Fix RBAC/UI dead ends.** Hide claim/product/document controls from reviewers, or allow the permitted subset; fix the CSV import hard-coded path and fake progress bar; fix the 9 missing icon IDs.

### P2 — hardening / polish

16. Remove dead code (`web/services.py`, `image_classifier_v2.py`, unused filters/monitoring) or wire it in; explain every module.
17. Make ID generation concurrency-safe (transaction/sequence), add pagination to analytics, and run a 10k-claim load test.
18. Harden security: no default `SECRET_KEY`, HTTPS/session settings, login throttling, upload content sniffing, retention/deletion policy.
19. Add a real `LICENSE`, fix the repo README broken links, and add the SRS-required screenshots of the working app.
20. Measure and document ≤5 s processing and 99% availability (or explicitly mark them unverified, as the report already does).

---

## 11. Verification log

| Check | Command / method | Result |
|---|---|---|
| Health readiness (as delivered) | `GET http://127.0.0.1:8765/health` (uvicorn, temp DB) | `{"status":"loading","models_ready":false,"python_model_ready":true,"gtm_model_ready":false}` |
| Live claim (as delivered) | `POST /claims/submit` as customer, no files | `HTTP 503` after **15.1 s**, `{"detail":"Models still loading. Retry in a moment."}` |
| TensorFlow (as delivered) | `importlib.util.find_spec` | `tensorflow False`; `torch False`; `keras/h5py False`; `easyocr False` |
| Health readiness (after fix) | `GET http://127.0.0.1:8766/health` | `{"status":"ok","models_ready":true,"python_model_ready":true,"gtm_model_ready":true}` |
| Live claim (after fix) | `POST /claims/submit`, no files | `HTTP 200` after **5.1 s**; Python `Manual Review` 0.9619; GTM `Manual Review` 0.6276; diff 0.3343; `Weak Match`; final `Manual Review Required` |
| GTM accuracy (after fix) | 225 test cards under TF 2.21 + tf-keras | **83/225 = 36.89%**, identical confusion matrix to §7.2 |
| Test tooling | venv package check | `pytest` now installed via `uv add`; Starlette 1.9 still needs `httpx2` for `TestClient` |
| Python model rescore | load artifacts, transform `data/test.csv`, inverse-transform labels | **0.9156**; CM `[[75,0,0],[0,70,5],[13,1,61]]`; train 0.9067 |
| Historical report | `model/v2/tabular_evaluation_report.json` | 0.92; CM `[[65,10,0],[0,70,5],[3,0,72]]` — **mismatch** |
| Label determinism | six-rule reconstruction over 1,500 rows | **1,500/1,500 = 100.0%** |
| Dataset cards | 03 mapping vs disk | **2,550/2,550 present**, 0 class/split mismatches |
| GTM stored-test accuracy | `05 .../METRICS.md`, `06 .../evaluation_run.json` | **36.89%**; Valid recall 0/75 |
| GTM live-rendered cards | `05 .../live_renderer_check.json` | **30/30 “Manual Review”**, 14/30 correct (46.7%) |
| GitHub history | `api.github.com/repos/.../commits`, `/contributors` | **1 commit**, **1 contributor**, repo created 2026-09-27, pushed 2026-09-28 |
| Blog | `web_fetch` published URL | HTTP 200; 2,974 words |
| Video | MP4 `mvhd` parse | **1,299.9 s ≈ 21.7 min**, 203.3 MB |
| SRS self-matrix | `16 .../SRS_BULLET_COVERAGE.csv` | 332 rows: 17 “Included in snapshot”, 214 “final build review required” |

---

## 12. Caveats

- I did not play the 21.7-minute video; its **content** is unverified beyond the coverage sheet and duration.
- After installing TensorFlow 2.21 + tf-keras I did load the GTM H5 and independently reproduced **36.89% (83/225)** with the same confusion matrix, so the package’s figure is confirmed.
- I installed `pytest` via uv but did not execute the full suite; the 35/42 results are taken from the package logs.
- Human understanding, per-member authorship, and “surprise modification” readiness cannot be verified from files.
- This audit judges the package **as delivered**. P0-1 has since been fixed in the working tree (§13); P0-2, P0-3, and P0-4 remain.

---

## 13. Post-audit runtime fix (2026-10-22)

After the first audit pass, TensorFlow was installed into a recreated Python 3.11 `.venv` with `uv`:

```powershell
uv add -r requirements.txt "tensorflow==2.21.0"
uv add "tf-keras"
```

**Why `tf-keras` is required:** TensorFlow 2.21 ships Keras 3, which cannot deserialize the Keras 2.15 `keras_model.h5`. Loading failed with:

```text
Layer "functional_4" expects 1 named input(s) ... but it received 2 input tensors.
```

Installing `tf-keras==2.21.0` and setting `TF_USE_LEGACY_KERAS=1` before TensorFlow is imported fixes this. The setting is now applied automatically at the top of `src/assurex_claim_engine/models/image_classifier.py`, and both packages are recorded in `requirements.txt` and `pyproject.toml` (with `uv.lock`).

**Verified after the fix:**

| Check | Result |
|---|---|
| GTM model load | ✅ `GTM Model loaded successfully!`; classes `['Valid Claim','Invalid Claim','Manual Review']`; output shape `(1, 3)`, probabilities sum to 1.0 |
| `/health` | ✅ `models_ready:true`, `python_model_ready:true`, `gtm_model_ready:true` |
| Live claim submission | ✅ HTTP 200 in **5.1 s**; dossier contains both model sections |
| Persisted dual-model result | Python `Manual Review` 0.9619; GTM `Manual Review` 0.6276; diff 0.3343; `Weak Match`; final `Manual Review Required` |
| GTM accuracy on 225 test cards | ❌ **36.89%** (83/225), unchanged — P0-2 remains |

**Operational notes:**

- **Why live GTM returned “Manual Review”:** the packaged v1 cards are **750×520** with an older layout; the live app now renders **600×600** with the rewritten renderer. Dataset v3 (§14) removes this mismatch, but the old model still fails on v3 (33.3%).
- TensorFlow import on this machine takes roughly 90–150 s, so the app is slow to become ready. Wait for `/health` to report `models_ready:true` before submitting.
- `run_app.bat` uses the `.venv` interpreter, which is now the 3.11 environment; it will work, but the browser may open before models finish loading.
- This fix makes the submission *runnable*; it does not make the GTM model accurate. The fusion engine will still route most claims to `Manual Review` because the GTM output is unreliable.

---

## 14. Post-audit data fix — dataset v3 (2026-10-22)

### What was wrong

- The packaged v1 cards are **750×520**, with a footer, an older layout, overlapping/clipped values, and no shipped script that produces that size.
- The live app rendered **840×500** (now **600×600** after the rewrite). Training and inference saw different distributions.
- `CLM-2026-0874` was labelled `Mismatch` while its user and OCR serials were identical.
- `warranty_start_date` was in every CSV but missing from `data_dictionary.json`.

### What changed

| Change | Location |
|---|---|
| Renderer rewritten: 600×600, square, wrapped/truncated values, no footer, no class-dependent styling; one function used offline and live | `dataset_generator/generate_summary_cards.py` |
| v3 structured dataset prepared from the frozen CSVs; one serial-mismatch record corrected; dictionary updated to v1.1 | `dataset_generator/prepare_dataset_v3.py`, `03 Common Dataset/structured_v3/` |
| 2,550 cards regenerated: 2,100 train / 225 val / 225 test | `03 Common Dataset/summary_cards_v3/` |
| Mapping, statistics, manifest, change log, validation report | `03 Common Dataset/structured_v3/` |
| Hard-check + render-parity validator | `dataset_generator/validate_dataset_v3.py` |
| Source-repo dictionary/stats/mapping and a v3 README | `02 Source Repository/data/` |
| Dataset guide updated | `03 Common Dataset/DATASET_GUIDE.md` |

### Verification

| Check | Result |
|---|---|
| Records / classes | 1,500; **500 / 500 / 500** |
| Splits | **1,050 / 225 / 225**, 350/75/75 per class, 0 Claim-ID overlap |
| Images | **2,550** (2,100 / 225 / 225), all 600×600 |
| Mapping | 2,550 rows; **0 missing files, 0 wrong sizes, 0 class/split mismatches** |
| Offline-vs-live render parity | **0 differences in 30 sampled claims** |
| Impossible serial mismatches | **0** after the fix |
| Validation | **PASSED hard checks**, 4 warnings |

### Old model baseline (pre-retrain)

The existing GTM model scores **33.3% (75/225)** on the final v3 test cards, predicting “Invalid Claim” for **all 225** (every Valid and every Manual Review card is called Invalid). Live v3 rendering is **26.7% (8/30)**, also predicting Invalid for all 30. The renderer fix removes the deployment mismatch but does not fix the model. Retraining starts from a **33.3%** baseline on v3 (36.89% on v1).

### Remaining data warnings (not silently rewritten)

- Labels are still **100% reproducible** from six conditions.
- `has_warranty_card` and `has_product_photo` are constant `True`.
- All 14 `duplicate_claim_flag` rows lack matching serial/invoice evidence.
- Only 2 records sit exactly on `remaining_warranty_days == 0`.

These are the next data-quality items if a more realistic benchmark is required.

---

## 15. GTM retrain result (2026-10-22)

A new GTM export was placed in `GTM Models/` at **14:42** (SHA-256 prefix `d104edab…`). The v3 evaluation harness now runs with the exact command:

```powershell
uv run python dataset_generator/evaluate_gtm_v3.py
```

The harness adds both the project root and `src/` to `sys.path`, so it no longer needs a manual `PYTHONPATH`.

### Results

| Metric | Old model | Retrained model | Gate |
|---|---:|---:|---:|
| v3 test accuracy (225) | 33.3% | **75.56%** (170/225) | ≥85% ❌ |
| v3 live-render accuracy (30) | 26.7% | **73.33%** (22/30) | ≥85% ❌ |
| Valid Claim recall | 0.0% | **73.3%** | >0 ✅ |
| Manual Review recall | 0.0% | **84.0%** | ≥70% ✅ |

Per-class test results:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Valid Claim | 0.671 | 0.733 | 0.701 | 75 |
| Invalid Claim | 0.981 | 0.693 | 0.813 | 75 |
| Manual Review | 0.700 | 0.840 | 0.764 | 75 |

Confusion matrix (rows actual, columns predicted Valid / Invalid / Manual):

```text
[[55,  1, 19],
 [15, 52,  8],
 [12,  0, 63]]
```

Predicted distribution: 82 Valid, 53 Invalid, 90 Manual Review. The model is no longer collapsed to one class.

### Diagnostics: where the 55 errors come from

- **Underfit, not overfit:** train sample **71.6%** (161/225), validation **71.1%** (160/225), test **75.6%** (170/225). The model does not memorise the training cards.
- **v3-trained confirmed:** on the old v1 cards the same model scores **33.3%**, predicting Invalid for all 225. It learned the v3 distribution, not the old one.
- **Expired warranty accounts for 22 of 55 errors.** There are 36 expired test cards; only 14 are correct. The rest become 15 Valid and 7 Manual Review, even though the card shows a negative remaining-days value.
- **Missing documents account for 11 of 55 errors.** 24 cards have `missing_documents_count > 0`; only 13 are correct. The missing-receipt subset (11 cards) has 6 errors.
- **19 Valid → Manual Review**, and **15 of those 19 have exactly one prior repair**. The card says “authorized”, but the model treats “1 repair” as risk.
- **Every error is low-confidence** (max 0.639); there are no high-confidence errors. A confidence threshold does **not** help — the best threshold (0.40) drops accuracy to 74.2%.
- Serial mismatch (13/13), contradiction (37/38), and excluded damage (26/26) are already strong. Product category is balanced across classes; no confound.
- **Headroom:** applying only `expired → Invalid` and `missing documents → Manual Review` would take the test score to **90.2%**. That is a diagnostic, not a shipping rule — the GTM model must learn those facts from the card.

### What to change, in order

1. **Confirm the run settings.** If the export used ~50 epochs, retrain the same v3 cards at 100–150 epochs. But train accuracy is only 71.6%, so epochs alone may not close the gap.
2. **Make the decision facts large and explicit.** The 224×224 input cannot read 26 px text. Add four status tiles (40–48 px) above the details:
   - `WARRANTY: ACTIVE / EXPIRING / EXPIRED` + remaining days
   - `DOCUMENTS: COMPLETE / MISSING n`
   - `REPAIRS: n AUTHORIZED / UNAUTHORIZED`
   - `SERIAL: MATCH / MISMATCH`
   Keep product/fault/age below. This directly targets 22 expired, 11 missing-doc, and 15 one-repair errors.
3. **Add targeted training examples** for those three groups. Do not add more easy cases or more variations until the card is legible.
4. **Then add variations/epochs** if the model is still underfit (train accuracy well below 90%).
5. **Do not tune a confidence threshold** — it reduces accuracy.
6. Use `val/` to choose revisions; evaluate `test/` once per frozen candidate.

The data work (§14) is complete; the remaining gap is card legibility plus underfitting, not the renderer or dataset split.

---

## 16. v4 status-tile dataset (2026-10-22)

The v4 card is built and validated. It replaces the seven-row text layout with four large
status tiles and keeps the details below:

- **WARRANTY**: ACTIVE / EXPIRING / EXPIRED + remaining days
- **DOCUMENTS**: COMPLETE / MISSING n
- **REPAIRS**: AUTHORIZED / 2+ REPAIRS / UNAUTHORIZED
- **SERIAL**: MATCH / PARTIAL / MISMATCH
- Details: product, fault/damage, age/warranty, contradiction/duplicate.

Dataset:

| Check | Result |
|---|---|
| Records / classes | 1,500; 500 / 500 / 500 |
| Splits | 1,050 / 225 / 225; 350/75/75 per class; 0 overlap |
| Images | 2,550 at 600×600; 2,100 train (two variations), 225 val, 225 test |
| Mapping | 2,550 rows; 0 missing, 0 wrong size, 0 class/split mismatch |
| Render parity | 0 failures in 30 sampled claims |
| Validation | `structured_v4/validation_report_v4.json` — **PASSED hard checks** |

Files: `03 Common Dataset/summary_cards_v4/`, `03 Common Dataset/structured_v4/`,
`dataset_generator/generate_summary_cards.py` (v4 renderer),
`dataset_generator/validate_dataset_v4.py`, `dataset_generator/evaluate_gtm_v4.py`, and
`03 Common Dataset/GTM_TRAINING_V4.md`.

The app now renders v4 cards live, so the old v3 H5 must be replaced before a dual-model
demo. Retraining instructions and acceptance gates are in `GTM_TRAINING_V4.md`.

---

## 17. v4 model result and website integration (2026-10-22)

The current `GTM Models/keras_model.h5` is the v4 export (SHA-256 `b69ad289…`, 18:16).

| Metric | Result | Gate |
|---|---:|---:|
| v4 test accuracy (225) | **78.22%** (176/225) | ≥85% ❌ |
| v4 live-render accuracy (30) | **86.67%** (26/30) | ≥85% ✅ |
| Invalid Claim recall | **100%** | — |
| Manual Review recall | **100%** | ≥70% ✅ |
| Valid Claim recall | **34.7%** (26/75) | — |

Per-class:

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Valid Claim | 1.000 | 0.347 | 0.515 |
| Invalid Claim | 0.974 | 1.000 | 0.987 |
| Manual Review | 0.615 | 1.000 | 0.761 |

Confusion matrix (rows actual; columns Valid / Invalid / Manual):

```text
[[26,  2, 47],
 [ 0, 75,  0],
 [ 0,  0, 75]]
```

The test gap is entirely Valid→Manual Review: **46 of 71 all-green Valid cards** are called
Manual Review. The cause is that **36 Manual Review cards are also all-green except for a
contradiction flag**, and that flag appears only in the 20 px detail text. At 224×224 the
model cannot separate the two groups. A diagnostic oracle using a prominent flags signal
scores **100%** on the same test set, so the remaining headroom is card legibility, not
model capacity.

### Integration verification

The website was tested end-to-end with the v4 model and v4 renderer:

| Check | Result |
|---|---|
| `/health` | `models_ready:true`, `python_model_ready:true`, `gtm_model_ready:true` |
| Live claim submission | **HTTP 200 in 3.8 s** |
| Persisted Python result | `Manual Review` 0.9619 |
| Persisted GTM result | `Manual Review` 1.0000 |
| Confidence difference | 0.0381 |
| Consistency | **Strong Match** |
| Final decision | `Manual Review Required` (four mandatory docs missing) |
| Saved summary card | 600×600, v4 status-tile layout |

The card renderer used live is pixel-identical to the v4 training cards for 30/30 sampled
claims. The v4 model is therefore integrated and working; the only unresolved SRS gate is
the **test** accuracy of 78.22% (live is 86.67%). Recovering Valid recall requires making
the contradiction/duplicate flag as prominent as the four status tiles.

---

*Prepared by an independent code audit. All findings above are traceable to a file, a command result, or a public URL recorded in §11.*
