# Evaluation (starter)

| issue_type | labelled | flagged | true_positive | false_positive | false_negative | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|
| EXPIRED_BAND | 4 | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FTE_IGNORED | 4 | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FX_CONVERSION_MISSING | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| INCOMPARABLE_GROUP | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNAPPROVED_ADJUSTMENT | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_HIGH | 6 | 6 | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_LOW | 6 | 6 | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| ALL | 29 | 29 | 29 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Recommended action matched the expected decision for 29 of 29 correctly found issues.

## Outlier threshold sweep

Current threshold: 0.08

| threshold | flagged | precision | recall | f1 |
|---|---|---|---|---|
| 0.05 | 55 | 0.218 | 1.000 | 0.358 |
| 0.06 | 24 | 0.500 | 1.000 | 0.667 |
| 0.07 | 15 | 0.800 | 1.000 | 0.889 |
| 0.08 | 12 | 1.000 | 1.000 | 1.000 |
| 0.09 | 11 | 1.000 | 0.917 | 0.957 |
| 0.10 | 10 | 1.000 | 0.833 | 0.909 |
| 0.12 | 9 | 1.000 | 0.750 | 0.857 |
