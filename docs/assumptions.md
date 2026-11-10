# Assumptions and Scope Decisions

The brief leaves several points open. Each assumption below states what was
decided and why. Anything that deviates from the brief is marked **Deviation**.

## Time and scope

| # | Assumption | Reason |
|---|---|---|
| A1 | Salary history covers 2024-01-01 to 2026-11-30. The pay review runs on a fixed snapshot date, 2026-12-01. | "3 years of salary history". A fixed date (never the system clock) keeps every run identical. |
| A2 | 40 roles x 5 levels = 200 role/level combinations, across 8 locations and 5 currencies. | Matches the required 200 combinations and gives enough currency variety to test conversion. |
| A3 | One compensation band exists per role, level, location and year (2024, 2025, 2026), so 4,800 bands. Each band is valid from 1 Jan to 31 Dec of its year. | The band ID convention ends in a year, and metrics must use effective-dated bands. |
| A4 | Band minimum is 80% of the midpoint and band maximum is 120%. Midpoints rise 4% each year. | A common, simple band shape. The exact width is not specified in the brief. |

## Data model

| # | Assumption | Reason |
|---|---|---|
| A5 | `SalaryRecord` is an append-only event table. Every hire, annual review, promotion, FTE change, relocation or adjustment adds a new row. No row is ever updated. | "Do not overwrite history." |
| A6 | Each salary record carries the role, level, location, FTE and currency that applied from its effective date. | This avoids a separate assignment-history table while still preserving full history. |
| A7 | In `SAL-<employee-id>-2026-01`, `2026` is the year of the effective date and `01` is a sequence number within that employee and year. | The brief does not define the last part. A sequence allows two changes in the same month without ID clashes. |
| A8 | Two extra tables are added: `FxRate` and `ProposalEvent`. A bridge table `ComparableGroupMember` links groups and employees. | Currency normalisation needs rates. The approval trail needs explicit events. Group membership is many-to-many. |
| A9 | `annual_amount` is the amount actually paid per year at the employee's FTE, in the record's currency. | This makes FTE normalisation a real calculation: full-time equivalent = amount / FTE. |
| A10 | Exchange rates are fixed synthetic values, one per currency per year, expressed against USD. | No external data is used, so there are no licensing questions. |

## Business rules

| # | Assumption | Reason |
|---|---|---|
| A11 | Compa-ratio = (annual_amount / FTE, converted to the band currency) / band midpoint. Band position = (that salary - band min) / (band max - band min). | Standard definitions. Both must use the band valid on the salary's effective date. |
| A12 | The documented, job-related factors are: time in level, latest performance rating, and a documented critical-skill premium. | These are the factors the brief names (performance evidence, tenure, promotion). |
| A13 | A comparable group is employees with the same role, level and location. If fewer than 5 people qualify, the group widens to the same role and level across all locations and records the rationale `SMALL_GROUP_WIDENED`. | Compa-ratio is already relative to the local band, so cross-location comparison is fair once widened. Groups under 5 are too small to judge. |
| A14 | An outlier is "unexplained" when pay differs from what the documented factors predict by more than a threshold, and no evidence record explains it. | "Outliers have contextual evidence." |
| A15 | Proposal lifecycle: DRAFT -> SUBMITTED -> HR_REVIEWED -> APPROVED -> APPLIED. A proposal can be REJECTED after SUBMITTED or HR_REVIEWED. | Gives a normal path and at least one exception path, with every step recorded as an event. |

## Anomalies and ground truth

| # | Assumption | Reason |
|---|---|---|
| A16 | `recorded_compa_ratio` on a salary record represents what the upstream HR system calculated at the time. Three edge cases (expired band, FTE ignored, currency conversion missing) are injected as wrong values in this field. | This lets the anomaly live in one labelled field, without corrupting unrelated rows. The solution recomputes the correct value and compares. |
| A17 | Anomaly labels live only in `ground_truth.csv`. No input table has an `issue_type` column. | "Never leak it into input features." |
| A18 | Each anomalous record carries at most one injected issue. | Keeps per-issue precision and recall easy to interpret. |

## Deliberate exclusions

| # | Decision | Reason |
|---|---|---|
| D1 | **Deviation:** No gender, ethnicity, age, names or other personal attributes are generated. | The brief asks for comparison against role, level, location and documented factors only. Leaving out protected attributes avoids sensitive data in a public repository. A real pay-equity study would add them under proper controls. |
| D2 | Bonuses, equity and benefits are out of scope. Only base salary is modelled. | Not requested, and it keeps the reconciliation checks exact. |
| D3 | Terminated employees keep their history but are excluded from the 2026 review. | You cannot adjust the pay of someone who has left. |
