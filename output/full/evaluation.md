# Evaluation (full)

| issue_type | labelled | flagged | true_positive | false_positive | false_negative | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|
| EXPIRED_BAND | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FTE_IGNORED | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FX_CONVERSION_MISSING | 30 | 30 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| INCOMPARABLE_GROUP | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| SYSTEMIC_DISPARITY | 3 | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNAPPROVED_ADJUSTMENT | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_HIGH | 39 | 50 | 39 | 11 | 0 | 0.780 | 1.000 | 0.876 |
| UNEXPLAINED_OUTLIER_LOW | 76 | 70 | 70 | 0 | 6 | 1.000 | 0.921 | 0.959 |
| ALL | 258 | 263 | 252 | 11 | 6 | 0.958 | 0.977 | 0.967 |

Recommended action matched the expected decision for 252 of 252 correctly found issues.

## Pay policy: estimated from data against the generator's values

The detector never sees the right-hand column. It is shown here only to check the estimate.

| parameter | estimated_by_detector | used_by_generator |
|---|---|---|
| Ratio with no tenure and a rating of 3 | 0.8918 | 0.9000 |
| Added per year in level | 0.0187 | 0.0200 |
| Years after which tenure stops counting | 6.0000 | 5.0000 |
| Added per rating point | 0.0278 | 0.0300 |
| Added per unit of documented premium | 1.0184 | 1.0000 |

## Outlier threshold sweep

Current threshold: 0.08

| threshold | flagged | precision | recall | f1 |
|---|---|---|---|---|
| 0.05 | 287 | 0.397 | 0.991 | 0.567 |
| 0.06 | 154 | 0.734 | 0.983 | 0.840 |
| 0.07 | 132 | 0.848 | 0.974 | 0.907 |
| 0.08 | 120 | 0.908 | 0.948 | 0.928 |
| 0.09 | 112 | 0.946 | 0.922 | 0.934 |
| 0.10 | 103 | 0.971 | 0.870 | 0.917 |
| 0.12 | 87 | 0.989 | 0.748 | 0.851 |
