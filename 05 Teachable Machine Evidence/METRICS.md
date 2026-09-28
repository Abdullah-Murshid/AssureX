# GTM model evaluation

Observed accuracy: 36.89% on 225 supplied test claims.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Valid Claim | 0.0000 | 0.0000 | 0.0000 | 75 |
| Invalid Claim | 0.3507 | 0.9867 | 0.5175 | 75 |
| Manual Review | 0.6429 | 0.1200 | 0.2022 | 75 |

Confusion matrix (actual rows; predicted columns; Valid, Invalid, Manual Review):
[[0, 71, 4], [0, 74, 1], [0, 66, 9]]

This is an agent-run reproducibility evaluation, not a claim of independent student execution. No training occurred in this run.