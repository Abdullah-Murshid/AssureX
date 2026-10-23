# Common dataset evidence

## v4 (2026-10-22) — canonical for GTM retraining

`summary_cards_v4/` contains **2,550 status-tile cards at 600×600**, rendered by the same
`render_claim_card()` function the web application uses. `structured_v4/` contains the
matching CSVs, dictionary, statistics, mapping, manifest and validation report.

- 1,500 unique claims: **500 Valid / 500 Invalid / 500 Manual Review**
- 1,050 / 225 / 225 records (70/15/15), 350/75/75 per class
- 2,100 training cards (1,050 claims × 2 variations: light + dark)
- 225 validation and 225 test cards (variation 1, the live style)
- Zero cross-split Claim IDs; all 2,550 mapping paths resolve; all images are 600×600
- Offline-vs-live render parity: **0 differences in 30 sampled claims**
- Validation report: `structured_v4/validation_report_v4.json` — **PASSED hard checks**

### Why v4

v3 fixed the renderer size and text overflow, but the v3 model was underfit (71.6% on its
own training cards). Of its 55 test errors, **22 were expired warranties** and **11 were
missing-document claims** — facts that were present as small text. v4 puts four large
status tiles at the top:

- **WARRANTY**: ACTIVE / EXPIRING / EXPIRED + remaining days
- **DOCUMENTS**: COMPLETE / MISSING n
- **REPAIRS**: AUTHORIZED / 2+ REPAIRS / UNAUTHORIZED
- **SERIAL**: MATCH / PARTIAL / MISMATCH

Claim details (product, fault/damage, age/warranty, contradiction/duplicate) remain below.
No prediction, confidence, final decision, or class label appears on the card.

### v4 commands

```powershell
uv run python dataset_generator/generate_summary_cards.py `
  --data-dir "../03 Common Dataset/structured_v4" `
  --output-dir "../03 Common Dataset/summary_cards_v4" `
  --metadata-dir "../03 Common Dataset/structured_v4"
uv run python dataset_generator/validate_dataset_v4.py
uv run python dataset_generator/evaluate_gtm_v4.py
```

## v3 (superseded)

`summary_cards_v3/` is the 600×600 seven-row text layout. It is kept for provenance and for
the 75.56% v3 model evaluation. It has the same records and labels as v4.

## v1 / v2 (historical)

`summary_cards/` is the original **750×520** set. `structured/` is the matching v1 CSV
corpus. The v2 card set had 2,053 split/class mismatches against the original CSVs and is
not presented as matching evidence.

## Known data limitations (reported, not hidden)

- Labels are still **100% reproducible** from six conditions (damage/unauthorized repair,
  contradiction, duplicate flag, serial mismatch, missing documents, remaining warranty).
- `has_warranty_card` and `has_product_photo` are constant `True`.
- All 14 `duplicate_claim_flag` rows lack matching serial/invoice evidence.
- Only 2 records sit exactly on `remaining_warranty_days == 0`.
- The data is synthetic; labels are not independent real-world adjudications.

These remain the next data-quality items if a more realistic benchmark is required.

Final dataset version: **v4**
Training corpus and model provenance: record after GTM retraining
Independent card-content and label verification: pending team review
