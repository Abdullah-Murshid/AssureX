# Python model evaluation

Observed accuracy: 91.56% on 225 supplied test claims.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Valid Claim | 0.8523 | 1.0000 | 0.9202 | 75 |
| Invalid Claim | 0.9859 | 0.9333 | 0.9589 | 75 |
| Manual Review | 0.9242 | 0.8133 | 0.8652 | 75 |

Confusion matrix (actual rows; predicted columns; Valid, Invalid, Manual Review):
[[75, 0, 0], [0, 70, 5], [13, 1, 61]]

This is an agent-run reproducibility evaluation, not a claim of independent student execution. No training occurred in this run.