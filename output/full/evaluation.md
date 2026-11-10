# Evaluation (full)

| issue_type | labelled | flagged | true_positive | false_positive | false_negative | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|
| EXPIRED_BAND | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FTE_IGNORED | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FX_CONVERSION_MISSING | 30 | 30 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| INCOMPARABLE_GROUP | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNAPPROVED_ADJUSTMENT | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_HIGH | 41 | 52 | 38 | 14 | 3 | 0.731 | 0.927 | 0.817 |
| UNEXPLAINED_OUTLIER_LOW | 78 | 75 | 75 | 0 | 3 | 1.000 | 0.962 | 0.980 |
| ALL | 259 | 267 | 253 | 14 | 6 | 0.948 | 0.977 | 0.962 |

Recommended action matched the expected decision for 253 of 253 correctly found issues.

## Outlier threshold sweep

Current threshold: 0.08

| threshold | flagged | precision | recall | f1 |
|---|---|---|---|---|
| 0.05 | 545 | 0.218 | 1.000 | 0.358 |
| 0.06 | 230 | 0.509 | 0.983 | 0.670 |
| 0.07 | 141 | 0.830 | 0.983 | 0.900 |
| 0.08 | 127 | 0.890 | 0.950 | 0.919 |
| 0.09 | 117 | 0.932 | 0.916 | 0.924 |
| 0.10 | 106 | 0.972 | 0.866 | 0.916 |
| 0.12 | 89 | 0.989 | 0.739 | 0.846 |
