# GTM retraining — dataset v4 (status tiles)

## Why v4

The v3 model reached 75.56% and was **underfit** (71.6% on its own training cards). The
errors were concentrated in facts that were present but too small at 224×224:

- 22/55 errors were **expired warranties**
- 11/55 were **missing documents**
- 15/19 Valid→Manual errors had **one authorized repair**

v4 replaces the 7-row text card with four large status tiles, so those facts are readable
after the 224×224 resize. The records, labels, and splits are unchanged from v3.

## 1. What to upload

Create a **new** Google Teachable Machine **Image Project → Standard image model**.
Class names exactly:

- `Valid Claim`
- `Invalid Claim`
- `Manual Review`

Upload **only** the v4 training cards:

| Class | Folder | Files |
|---|---|---:|
| Valid Claim | `03 Common Dataset/summary_cards_v4/train/Valid Claim/` | 700 |
| Invalid Claim | `03 Common Dataset/summary_cards_v4/train/Invalid Claim/` | 700 |
| Manual Review | `03 Common Dataset/summary_cards_v4/train/Manual Review/` | 700 |

**Do not upload** `val/` or `test/`. They are held out.

## 2. Training settings

- Epochs: **100–150** (the v3 model was underfit; give it room)
- Batch size: 16 or 32
- Learning rate: default (0.001)
- Keep the classes balanced at 700/700/700

The v4 card exposes `EXPIRED`, `MISSING`, `AUTHORIZED`/`UNAUTHORIZED`, and
`MATCH`/`MISMATCH` as large tile values. Do not crop or resize the cards before upload.

## 3. Export

Export **TensorFlow → Keras** and keep both files:

- `keras_model.h5`
- `labels.txt` (exported order)

Replace:

```
GTM Models/keras_model.h5
GTM Models/labels.txt
```

The app sets `TF_USE_LEGACY_KERAS=1` automatically, so the Keras 2 H5 loads under
TensorFlow 2.21 + `tf-keras`.

## 4. Evaluate

From `02 Source Repository`:

```powershell
uv run python dataset_generator/evaluate_gtm_v4.py
```

It reports:

- 225 held-out v4 test cards: accuracy, per-class P/R/F1, confusion matrix
- 30 cards rendered by the live app (v4)
- misclassified examples and predicted distribution

Report: `05 Teachable Machine Evidence/v4_evaluation.json`.

## 5. Acceptance gates

| Gate | Required |
|---|---:|
| v4 test accuracy | **≥ 85%** |
| v4 live-render accuracy (30) | **≥ 85%** |
| Manual Review recall | **≥ 70%** |
| Valid Claim recall | **> 0** |
| Expired-warranty accuracy | should rise sharply from 14/36 |
| Missing-document accuracy | should rise sharply from 13/24 |

The previous v3 baseline was 75.56% test / 73.33% live.

## 6. If a gate fails

- If **train accuracy on v4 training cards is still < 85%**: the model is underfit — train
  longer, then consider more variations.
- If **train is high but test/live is low**: add label-preserving variations (font size,
  spacing, background, compression), not new facts.
- If **expired/missing are still wrong**: check that the v4 card is displayed at full
  resolution and that the tile values are not cropped.

Do not upload `val/` or `test/` to fix errors. Do not tune on the test set.

## 7. Evidence to capture

- GTM project link
- Screenshots of the three classes and image counts (700/700/700)
- Training settings (epochs, batch size, learning rate)
- Training observations and retraining history
- Exported model hash and version label (e.g. `gtm-v4-2026-10-22`)
- `v4_evaluation.json` and sample v4 cards
