# Execution and evaluator guide

## Setup and login

Follow documentation/INSTALLATION.md and initialize a fresh synthetic evaluator database. Open http://127.0.0.1:8000. Register a customer/service account, or use the synthetic seed logins listed in the installation guide. Reviewer and administrator access must be provisioned through authorized setup, not public self-registration. Verify /health before the dual-model demonstration.

## Products and warranty information

Open Products, choose New product and enter name, category, brand, model, serial, purchase date, price, retailer and warranty duration. Open Warranties to inspect derived start/expiry, remaining days and status. The observed baseline only stores standard product duration plus category rules; the team's final extended-warranty/provider/coverage workflow is [[WARRANTY_WORKFLOW]]. Do not describe that blank as already implemented.

## Evidence and verification

Open Document vault, select the relevant product and evidence type, upload a supported synthetic file, then open Verify. Review and correct purchase date, invoice, product/model/serial, retailer, amount and duration fields as supported. Save corrections; review any hash duplicate warning. The final OCR coverage and correction-before-submit flow require final team validation. Upload additional warranty cards, product/serial/damage photos, diagnostic/repair records or fault videos as required by the category policy.

## Claim preparation and submission

Choose New claim and select the registered product. Enter fault category, occurrence date, damage, description and repair details; attach the correct vault documents/evidence. Run preparation checks, resolve missing fields/documents, inspect deadlines and contradictions, then submit. The server creates Claim ID, computes derived features, invokes the Python classifier, renders the Claim Summary Card and invokes GTM if available. These steps are automatic in the current route; do not invent separate prediction buttons.

## Interpret the dossier

The Python prediction includes Valid Claim, Invalid Claim and Manual Review probabilities; the highest is its top-class confidence. The card must show claim facts without that prediction or the final decision. GTM independently predicts from the card with its own three probabilities. Compare class agreement and abs(Python top minus GTM top), then inspect Strong Match, Acceptable Match, Weak Match, Model Disagreement or Uncertain Result.

Inspect passed/failed policies, missing evidence, date/model/serial contradictions and duplicate reasons. Different predictions, uncertainty, missing evidence or adverse rules require manual review. An unavailable vision model must display Unavailable rather than fabricated probabilities. The supplied baseline GTM fails the accuracy gate; final runtime/model evidence must be refreshed before filming a completed dual-model workflow.

## Reviewer and administrator

Log in as reviewer, open Review queue, inspect the dossier, add a meaningful reason and approve, reject or request information. The original AI result remains stored; status/reviewer actions are audited. Log in as admin to inspect Analytics, Policies and Audit logs. Update allowed JSON-backed policy fields and verify the chosen release reload behavior. Final notifications, expanded analytics/export and full lifecycle instructions are [[FINAL_WORKFLOW_NOTES]], supplied after the implementation team finishes.

## Track status and export

Open the claim dossier from the dashboard to inspect its current status. Use Download report to obtain claim/evidence/model/comparison/rule/contradiction/reviewer details. The baseline administrator CSV export covers claims. Draft/resubmission/close transitions, selected product/warranty/analytics exports and final notification behavior must be confirmed in the final build. Record screenshots and actual test outcomes rather than filling them with expected values.

## Tests and evaluator scenarios

Run python -m pytest tests -q in an isolated copy with its own database. Follow 08 Test Cases and Results/MANDATORY_SCENARIOS.csv for valid, invalid, manual-review, expiry, missing-evidence, duplicate, contradiction, serial mismatch, unauthorized repair, boundary date and model disagreement. Label unit-test fixtures separately from genuine model inference. Demo MP4 [[DEMO_MP4_PATH]], published blog [[BLOG_URL]], release commit [[RELEASE_COMMIT]].
