# GTM Model Diagnosis — why Valid claims get "Manual Review"

## TL;DR

The deployed Teachable Machine export is **underfit**, not a card-legibility
problem. It scores only **78.6% on its own training cards** (78.2% test), and
**51.6%** on the 95 test cards where the four status tiles are all green.

A candidate head-fix — same MobileNetV2 base, retrained head — scores **100%**
on the held-out v4 test set and **100%** on the live-rendered check, while
leaving `keras_model.h5` untouched. A six-tile v6 card design is also ready if
you prefer to retrain properly in Teachable Machine.

## Update — v6 model installed

You retrained in Teachable Machine on the v6 cards and replaced the model files.

- New model SHA-256: `541935fe8d3861b63ff7a765a7fde1731a4864d7891577eaabf0890360771337`
- v6 test cards: **225/225 = 100%** (75/75/75)
- Live-render check: **30/30 = 100%**
- v4/v5 cards score 33% — expected, the new model only knows v6
- Live renderer switched to `render_claim_card_v6` in both `src/assurex_claim_engine/web/app.py` and `backend/restapi/services/claim_flow.py`
- Fixed the DOCUMENTS tile: it now counts **policy-mandatory documents only**. It previously counted all four evidence types, so a valid claim with receipt + warranty card still rendered `MISSING 2` and was sent to Manual Review.
- Live verification: `CLM-2026-0019` → Python **Valid Claim**, GTM **Valid Claim** (1.0), final **Likely Valid**, status **Approved**.

Evaluate the installed model (cmd.exe, single line — no backticks):

```bat
uv run python dataset_generator\evaluate_gtm_v4.py --model "GTM Models\keras_model.h5" --structured ".. Common Dataset\structured_v4" --images ".. Common Dataset\summary_cards_v6" --out ".. Teachable Machine Evidence6_evaluation.json"
```

The evaluator auto-detects `v6` in the `--images` path and renders the live check with the v6 renderer.

---

## Evidence

### 1. The model cannot fit its training data

| Split | Accuracy | Valid recall |
| --- | --- | --- |
| Train (1,050 cards, v1) | **78.57%** (825/1050) | 35.7% |
| Test (225 cards) | **78.22%** (176/225) | 34.7% |

217 of 350 training Valid cards are classified as Manual Review. Train accuracy
≈ test accuracy is the signature of **underfitting**, not overfitting.

### 2. All-green cards are where it fails

v4 cards have four status tiles (warranty, documents, repairs, serial). 95 test
cards are all-green — 71 Valid and 24 Invalid — and differ only in small detail
text:

| Visual family | Cards | v4 accuracy |
| --- | --- | --- |
| All-green, no flags | 95 | **51.6%** |
| All-green + contradiction flag | 36 | 100% |
| Expired | 36 | 100% |
| Missing documents | 24 | 100% |
| Serial mismatch | 13 | 100% |
| Unauthorized repair | 13 | 100% |

Among the 71 Valid all-green cards: 25 correct, 44 → Manual Review, 2 → Invalid.
The 24 Invalid all-green cards are invalid because **accidental damage** was
reported (liquid spill, improper wiring, cosmetic wear…), which only appears in
the small "Fault / Damage" line.

### 3. The cards are learnable — the head is the weak link

A frozen MobileNetV2 (alpha 0.35) plus a logistic-regression head, exactly the
kind of transfer learning Teachable Machine performs, reaches **100%** on the
same v4 test cards. The same experiment on v6 cards also reaches 100%
(`05 Teachable Machine Evidence/v6_separability.json`).

So the information is present; the deployed head was not trained enough.

### 4. Architecture of the deployed export

```
MobileNetV2 (alpha=0.35) → GAP(1280) → Dense(100, relu) → Dense(3, softmax, no bias)
538,608 parameters
```

This is the standard TM image architecture. Nothing is corrupted; it is simply
badly fit.

---

## Candidate fix (not deployed)

`GTM Models/keras_model_headfix.h5` — same base weights, new Dense(100)+Dense(3)
head trained for 150 epochs on the frozen 1280-d features of the 2,100 v4 train
cards.

| Check | Result |
| --- | --- |
| Held-out v4 test (225) | **100%** (75/75/75) |
| Saved file, reloaded through the app loader | **100%** |
| Live-renderer check (30) | **100%** |

SHA-256: `72cffc7240aab03eff481ecb47ec6d929595ad37d89a3f1e563cd461db1e8cd7`
Deployed model remains `b69ad289…` and is unchanged.

To switch the live app:

```powershell
Copy-Item "GTM Models\keras_model_headfix.h5" "GTM Models\keras_model.h5"
# restart the backend so the registry reloads the model
```

Caveat: the candidate is validated on synthetic, held-out cards. Before the
final submission, run a few real claims through it.

---

## Recommended proper fix: retrain in Teachable Machine on v6 cards

The six-tile v6 renderer adds the two signals that were only tiny text:

```
FLAGS      NONE / CONTRADICTION / DUPLICATE / BOTH FLAGS
DAMAGE     NONE / DAMAGE
WARRANTY   ACTIVE / EXPIRING / EXPIRED
DOCUMENTS  COMPLETE / MISSING n
REPAIRS    AUTHORIZED / 2+ REPAIRS / UNAUTHORIZED
SERIAL     MATCH / PARTIAL / MISMATCH / UNVERIFIED
```

v6 dataset generated from the same 1,050/225/225 split:

- `03 Common Dataset/summary_cards_v6/` — 2,550 cards (2,100 train, 225 val, 225 test)
- `03 Common Dataset/summary_cards_v6/dataset_statistics_v6.json`

In Teachable Machine: three classes, **700 samples per class**, default
augmentation, **100–150 epochs**. Then evaluate:

```powershell
uv run python dataset_generator/evaluate_gtm_v4.py `
  --model "GTM Models\keras_model.h5" `
  --structured "..\03 Common Dataset\structured_v4" `
  --images "..\03 Common Dataset\summary_cards_v6" `
  --out "..\05 Teachable Machine Evidence\v6_evaluation.json"
```

If the v6 model passes ≥85%, switch the live renderer from
`render_claim_card` (v4) to `render_claim_card_v6` in
`src/assurex_claim_engine/web/app.py` and `backend/restapi/services/claim_flow.py`,
then re-run the live-render check so training and inference stay identical.

v6 alone is not sufficient without retraining: the deployed v4 model has never
seen those tiles.

---

## Files added

| File | Purpose |
| --- | --- |
| `dataset_generator/generate_summary_cards_v6.py` | six-tile v6 renderer + dataset generator |
| `dataset_generator/validate_v6_separability.py` | frozen-feature separability check |
| `dataset_generator/repair_gtm_head.py` | trains the candidate head, evaluates, saves it |
| `GTM Models/keras_model_headfix.h5` | candidate model (not deployed) |
