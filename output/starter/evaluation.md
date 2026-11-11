# Evaluation (starter)

| issue_type | labelled | flagged | true_positive | false_positive | false_negative | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|
| EXPIRED_BAND | 4 | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FTE_IGNORED | 4 | 4 | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FX_CONVERSION_MISSING | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| INCOMPARABLE_GROUP | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNAPPROVED_ADJUSTMENT | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_HIGH | 6 | 6 | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_LOW | 6 | 5 | 5 | 0 | 1 | 1.000 | 0.833 | 0.909 |
| ALL | 29 | 28 | 28 | 0 | 1 | 1.000 | 0.966 | 0.982 |

Recommended action matched the expected decision for 28 of 28 correctly found issues.

## Pay policy: estimated from data against the generator's values

The detector never sees the right-hand column. It is shown here only to check the estimate.

| parameter | estimated_by_detector | used_by_generator |
|---|---|---|
| Ratio with no tenure and a rating of 3 | 0.8785 | 0.9000 |
| Added per year in level | 0.0295 | 0.0200 |
| Years after which tenure stops counting | 4.0000 | 5.0000 |
| Added per rating point | 0.0270 | 0.0300 |
| Added per unit of documented premium | 0.9769 | 1.0000 |

## Outlier threshold sweep

Current threshold: 0.08

| threshold | flagged | precision | recall | f1 |
|---|---|---|---|---|
| 0.05 | 52 | 0.231 | 1.000 | 0.375 |
| 0.06 | 29 | 0.414 | 1.000 | 0.585 |
| 0.07 | 16 | 0.750 | 1.000 | 0.857 |
| 0.08 | 11 | 1.000 | 0.917 | 0.957 |
| 0.09 | 11 | 1.000 | 0.917 | 0.957 |
| 0.10 | 9 | 1.000 | 0.750 | 0.857 |
| 0.12 | 8 | 1.000 | 0.667 | 0.800 |
