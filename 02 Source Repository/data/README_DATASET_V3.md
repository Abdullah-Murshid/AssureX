# Dataset v3 (2026-10-22)

The canonical retraining dataset lives in the submission's dataset deliverable:

- Images: `../../03 Common Dataset/summary_cards_v3/`
- Structured data, mapping, dictionary, statistics, manifest:
  `../../03 Common Dataset/structured_v3/`

## Why v3 exists

The original cards in `03 Common Dataset/summary_cards/` are **750×520** with an older
layout and a footer. The live application renders **600×600** with the rewritten
`render_claim_card()`. Training on the old set and predicting on live cards is a domain
shift; it is the main reason the previous GTM model returned “Manual Review” for every
live card.

v3 regenerates all 2,550 cards with the live renderer:

- 600×600 square, no footer, no class-dependent styling
- text wrapped/truncated inside its column; no overlap or clipping
- 2,100 train images (1,050 claims × 2 variations)
- 225 validation + 225 test images (variation 1, the live style)
- all mapping paths resolve; 0 cross-split Claim IDs
- offline-vs-live render parity: 0 differences in 30 sampled claims

## Files in this folder

- `data_dictionary.json` — v3 dictionary (adds `warranty_start_date`)
- `dataset_statistics_v3.json` — counts and card metadata
- `claim_id_to_image_mapping_v3.csv` — 2,550 image mappings

`data/train.csv`, `val.csv`, `test.csv` and `processed/claims_dataset.csv` remain the
frozen v1 records. The v3 splits with the one serial-mismatch correction are in
`03 Common Dataset/structured_v3/`.

## Commands

From `02 Source Repository`:

```powershell
uv run python dataset_generator/prepare_dataset_v3.py
uv run python dataset_generator/generate_summary_cards.py `
  --data-dir "../03 Common Dataset/structured_v3" `
  --output-dir "../03 Common Dataset/summary_cards_v3" `
  --metadata-dir "../03 Common Dataset/structured_v3"
uv run python dataset_generator/validate_dataset_v3.py
```

The validator reports hard failures and keeps the known label issues as warnings
(deterministic labels, constant columns, unsupported duplicate flags, thin boundary cases).

## Known limitations

v3 fixes the image pipeline, not the label design. See
`../../03 Common Dataset/DATASET_GUIDE.md` for the remaining data-quality items.
