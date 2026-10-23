# GTM model evaluation

Observed accuracy: 78.22% on 225 supplied test claims.

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Valid Claim | 1.0000 | 0.3467 | 0.5149 | 75 |
| Invalid Claim | 0.9740 | 1.0000 | 0.9868 | 75 |
| Manual Review | 0.6148 | 1.0000 | 0.7614 | 75 |

Confusion matrix (actual rows; predicted columns; Valid, Invalid, Manual Review):
[[26, 2, 47], [0, 75, 0], [0, 0, 75]]

This is an agent-run reproducibility evaluation, not a claim of independent student execution. No training occurred in this run.