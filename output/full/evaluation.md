# Evaluation (full)

| issue_type | labelled | flagged | true_positive | false_positive | false_negative | precision | recall | f1 |
|---|---|---|---|---|---|---|---|---|
| EXPIRED_BAND | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FTE_IGNORED | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| FX_CONVERSION_MISSING | 30 | 30 | 30 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| INCOMPARABLE_GROUP | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNAPPROVED_ADJUSTMENT | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| UNEXPLAINED_OUTLIER_HIGH | 41 | 52 | 41 | 11 | 0 | 0.788 | 1.000 | 0.882 |
| UNEXPLAINED_OUTLIER_LOW | 78 | 72 | 72 | 0 | 6 | 1.000 | 0.923 | 0.960 |
| ALL | 259 | 264 | 253 | 11 | 6 | 0.958 | 0.977 | 0.967 |

Recommended action matched the expected decision for 253 of 253 correctly found issues.

## Pay policy: estimated from data against the generator's values

The detector never sees the right-hand column. It is shown here only to check the estimate.

| parameter | estimated_by_detector | used_by_generator |
|---|---|---|
| Ratio with no tenure and a rating of 3 | 0.8921 | 0.9000 |
| Added per year in level | 0.0186 | 0.0200 |
| Years after which tenure stops counting | 6.0000 | 5.0000 |
| Added per rating point | 0.0277 | 0.0300 |
| Added per unit of documented premium | 1.0181 | 1.0000 |

## Outlier threshold sweep

Current threshold: 0.08

| threshold | flagged | precision | recall | f1 |
|---|---|---|---|---|
| 0.05 | 299 | 0.395 | 0.992 | 0.565 |
| 0.06 | 160 | 0.731 | 0.983 | 0.839 |
| 0.07 | 137 | 0.847 | 0.975 | 0.906 |
| 0.08 | 124 | 0.911 | 0.950 | 0.930 |
| 0.09 | 116 | 0.948 | 0.924 | 0.936 |
| 0.10 | 107 | 0.972 | 0.874 | 0.920 |
| 0.12 | 89 | 0.989 | 0.739 | 0.846 |
