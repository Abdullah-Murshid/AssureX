# Dataset v4 (2026-10-22) — status-tile cards

The canonical retraining dataset is now **v4**:

- Images: `../../03 Common Dataset/summary_cards_v4/`
- Structured records, mapping, dictionary, statistics, manifest, validation:
  `../../03 Common Dataset/structured_v4/`

## Why v4

v3 fixed the renderer size and text overflow, but the v3 GTM model was **underfit**
(71.6% on its own training cards) and 33 of its 55 test errors came from two facts:

- **22 expired warranties** (36 expired cards, only 14 correct)
- **11 missing-document claims** (24 cards, only 13 correct)

Those facts were present as small text. v4 makes them large status tiles:

- WARRANTY: `ACTIVE` / `EXPIRING` / `EXPIRED` + remaining days
- DOCUMENTS: `COMPLETE` / `MISSING n`
- REPAIRS: `AUTHORIZED` / `2+ REPAIRS` / `UNAUTHORIZED`
- SERIAL: `MATCH` / `PARTIAL` / `MISMATCH`

The records, labels, and splits are unchanged from v3. Only the card layout changed.

## Counts

- 1,500 records: 500 Valid / 500 Invalid / 500 Manual Review
- 1,050 / 225 / 225 split, 350/75/75 per class
- 2,550 cards at 600×600: 2,100 train (2 variations), 225 val, 225 test
- 0 cross-split Claim IDs; 0 missing images; 0 class/split mapping mismatches
- Offline-vs-live render parity: 0 failures in 30 sampled claims

## Commands

From `02 Source Repository`:

```powershell
uv run python dataset_generator/generate_summary_cards.py `
  --data-dir "../03 Common Dataset/structured_v4" `
  --output-dir "../03 Common Dataset/summary_cards_v4" `
  --metadata-dir "../03 Common Dataset/structured_v4"

uv run python dataset_generator/validate_dataset_v4.py
uv run python dataset_generator/evaluate_gtm_v4.py
```

## Files here

- `data_dictionary.json` — v4 dictionary (card_version v4)
- `dataset_statistics_v4.json`
- `claim_id_to_image_mapping_v4.csv`

The older v3 files remain in `03 Common Dataset/` for provenance. The v1/v2 history is in
`03 Common Dataset/DATASET_GUIDE.md`.
