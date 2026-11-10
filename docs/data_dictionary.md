# Data Dictionary

Conventions used in every table:

- **Req** = required (Y) or optional (N). Optional fields are empty when not applicable.
- Dates are `YYYY-MM-DD`. Money is a whole number in the stated currency, per year.
- IDs are immutable, zero-padded and never reused.
- PK = primary key (unique). FK = foreign key (must exist in the parent table).

## Relationship overview

| Parent | Child | Cardinality | Notes |
|---|---|---|---|
| Role | CompensationBand | 1:N | |
| Level | CompensationBand | 1:N | |
| Location | CompensationBand | 1:N | |
| Employee | SalaryRecord | 1:N | At least one (the HIRE or OPENING_BALANCE record) |
| CompensationBand | SalaryRecord | 1:N | The band the source system compared against |
| Employee | PerformanceEvidence | 1:N | Optional: new hires may have none |
| Employee | Promotion | 1:N | Optional |
| Promotion | SalaryRecord | 1:1 | Each promotion creates exactly one salary record |
| Employee | Tenure | 1:1 | One row per employee at the snapshot date |
| Employee | Employee (manager) | 1:N | Optional self-reference |
| ComparableGroup | Employee | N:M | Through bridge table ComparableGroupMember |
| Employee | AdjustmentProposal | 1:N | Optional |
| ComparableGroup | AdjustmentProposal | 1:N | The group used as evidence |
| AdjustmentProposal | ProposalEvent | 1:N | At least one (creation as DRAFT) |
| AdjustmentProposal | SalaryRecord | 1:0..1 | Only APPLIED proposals create a salary record |

## Role (master)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| role_id | text | Y | PK. 3-4 uppercase letters, e.g. `SWE` |
| role_name | text | Y | Unique |
| job_family | text | Y | One of 8 families, e.g. `ENGINEERING`, `SALES` |
| base_mid_usd | integer | Y | > 0. Level-1 midpoint in USD before location and year factors |

## Level (master)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| level_id | text | Y | PK. `L1` to `L5` |
| level_name | text | Y | Unique |
| level_rank | integer | Y | 1 to 5, unique |
| mid_multiplier | decimal | Y | > 0, increases with level_rank |

## Location (master)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| location_id | text | Y | PK. 3 uppercase letters, e.g. `BLR` |
| city | text | Y | |
| country | text | Y | |
| currency_code | text | Y | `INR`, `USD`, `GBP`, `EUR`, `SGD` |
| geo_factor | decimal | Y | > 0. Local pay level relative to the USD baseline |

## FxRate (reference)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| currency_code | text | Y | PK part 1 |
| rate_year | integer | Y | PK part 2. 2024, 2025 or 2026 |
| units_per_usd | decimal | Y | > 0. USD is always 1.0 |

## CompensationBand (master, effective-dated)

ID format: `BAND-<role>-<level>-<location>-<year>`, e.g. `BAND-SWE-L3-BLR-2026`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| band_id | text | Y | PK |
| role_id | text | Y | FK to Role |
| level_id | text | Y | FK to Level |
| location_id | text | Y | FK to Location |
| band_year | integer | Y | 2024, 2025 or 2026 |
| currency_code | text | Y | Must equal the location's currency |
| band_min | integer | Y | = round(band_mid x 0.80) |
| band_mid | integer | Y | Derived from role, level, location, year and FX rate |
| band_max | integer | Y | = round(band_mid x 1.20) |
| effective_from | date | Y | 1 Jan of band_year |
| effective_to | date | Y | 31 Dec of band_year. Must be after effective_from |

Rules: band_min < band_mid < band_max. No two bands for the same role, level and location overlap in dates.

## Employee (master)

ID format: `EMP-000001`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| employee_id | text | Y | PK |
| hire_date | date | Y | On or before 2026-11-30 |
| employment_status | text | Y | `ACTIVE`, `TERMINATED` |
| termination_date | date | N | Required only when TERMINATED. Must be after hire_date |
| manager_employee_id | text | N | FK to Employee. Never the employee themself |

## SalaryRecord (event, append-only)

ID format: `SAL-<employee-id>-<year>-<seq>`, e.g. `SAL-EMP-000001-2026-01`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| salary_record_id | text | Y | PK |
| employee_id | text | Y | FK to Employee |
| effective_date | date | Y | On or after hire_date and 2024-01-01. Strictly later than the employee's previous record |
| role_id | text | Y | FK to Role |
| level_id | text | Y | FK to Level |
| location_id | text | Y | FK to Location |
| band_id | text | Y | FK to CompensationBand. The band the source system compared against |
| currency_code | text | Y | Currency the salary is paid in |
| fte | decimal | Y | 0.50, 0.60, 0.80 or 1.00 |
| annual_amount | integer | Y | > 0. Actual pay per year at this FTE, in currency_code |
| change_reason | text | Y | `OPENING_BALANCE`, `HIRE`, `ANNUAL_REVIEW`, `PROMOTION`, `FTE_CHANGE`, `RELOCATION`, `ADJUSTMENT` |
| proposal_id | text | N | FK to AdjustmentProposal. Required only when change_reason is ADJUSTMENT |
| recorded_compa_ratio | decimal | Y | 4 decimal places. As calculated by the source system |

Rules: the first record per employee is HIRE on the hire date (hired in 2024 or later) or OPENING_BALANCE on 2024-01-01 (hired earlier). The currency can differ from the band's currency after a relocation; the compa-ratio calculation converts it.

## PerformanceEvidence (event)

ID format: `PERF-<employee-id>-<year>-<seq>`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| evidence_id | text | Y | PK |
| employee_id | text | Y | FK to Employee |
| evidence_type | text | Y | `ANNUAL_RATING`, `CRITICAL_SKILL_PREMIUM` |
| evidence_date | date | Y | On or after hire_date |
| review_year | integer | Y | 2024, 2025 or 2026 |
| rating | integer | N | 1 to 5. Required only for ANNUAL_RATING |
| premium_pct | decimal | N | 5 to 20. Required only for CRITICAL_SKILL_PREMIUM |

Rule: at most one ANNUAL_RATING per employee per review_year.

## Promotion (event)

ID format: `PROMO-<employee-id>-<seq>`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| promotion_id | text | Y | PK |
| employee_id | text | Y | FK to Employee |
| effective_date | date | Y | After hire_date |
| from_level_id | text | Y | FK to Level |
| to_level_id | text | Y | FK to Level. Rank must be exactly from_level rank + 1 |
| salary_record_id | text | Y | FK to SalaryRecord. That record must have change_reason PROMOTION and the same date |

## Tenure (derived snapshot)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| employee_id | text | Y | PK. FK to Employee |
| as_of_date | date | Y | The snapshot date, 2026-12-01, or the termination date for employees who left |
| company_tenure_months | integer | Y | Whole months from hire_date to as_of_date |
| level_tenure_months | integer | Y | Whole months since the latest promotion, or since hire. Never more than company_tenure_months |

## ComparableGroup

ID format: `GRP-2026-000001`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| group_id | text | Y | PK |
| grouping_basis | text | Y | `ROLE_LEVEL_LOCATION`, `ROLE_LEVEL`, `FAMILY_LEVEL`, `CUSTOM` |
| role_id | text | N | FK to Role. Filled for ROLE_LEVEL_LOCATION and ROLE_LEVEL |
| level_id | text | N | FK to Level. Empty only for CUSTOM |
| location_id | text | N | FK to Location. Filled only for ROLE_LEVEL_LOCATION |
| job_family | text | N | Filled only for FAMILY_LEVEL |
| rationale | text | N | Required whenever the basis is not ROLE_LEVEL_LOCATION |
| member_count | integer | Y | Must equal the number of bridge rows for this group |

## ComparableGroupMember (bridge)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| group_id | text | Y | PK part 1. FK to ComparableGroup |
| employee_id | text | Y | PK part 2. FK to Employee |

## AdjustmentProposal

ID format: `ADJ-2026-000001`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| proposal_id | text | Y | PK |
| employee_id | text | Y | FK to Employee. Must be ACTIVE. One proposal per employee per review |
| group_id | text | Y | FK to ComparableGroup. The employee must be a member |
| basis_salary_record_id | text | Y | FK to SalaryRecord. The employee's latest record at creation |
| created_date | date | Y | On or after 2026-12-01. Equals the date of the first event |
| current_compa_ratio | decimal | Y | Recomputed correctly from source records |
| group_median_compa_ratio | decimal | Y | Median of the group, as evidence |
| target_compa_ratio | decimal | Y | Greater than current_compa_ratio |
| proposed_annual_amount | integer | Y | Greater than the current amount. Never above band_max at the employee's FTE |
| increase_pct | decimal | Y | = (proposed - current) / current x 100 |
| evidence_summary | text | Y | Short code-built sentence listing the factors checked |
| status | text | Y | Must equal the to_status of the proposal's latest event |

## ProposalEvent (event, append-only approval trail)

ID format: `ADJEVT-<proposal number>-<seq>`, e.g. `ADJEVT-2026-000001-01`.

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| event_id | text | Y | PK |
| proposal_id | text | Y | FK to AdjustmentProposal |
| event_seq | integer | Y | Starts at 1, no gaps |
| event_date | date | Y | Never earlier than the previous event's date |
| from_status | text | N | Empty only for the first event |
| to_status | text | Y | `DRAFT`, `SUBMITTED`, `HR_REVIEWED`, `APPROVED`, `REJECTED`, `APPLIED` |
| actor_role | text | Y | `MANAGER`, `HR_PARTNER`, `COMP_COMMITTEE`, `SYSTEM` |

Allowed transitions: DRAFT -> SUBMITTED -> HR_REVIEWED -> APPROVED -> APPLIED, plus SUBMITTED -> REJECTED and HR_REVIEWED -> REJECTED. REJECTED and APPLIED are final.

## ground_truth (labels, kept separate from all input tables)

| Field | Type | Req | Allowed values / rule |
|---|---|---|---|
| ground_truth_id | text | Y | PK. `GT-000001` |
| issue_type | text | Y | `EXPIRED_BAND`, `FTE_IGNORED`, `FX_CONVERSION_MISSING`, `UNAPPROVED_ADJUSTMENT`, `INCOMPARABLE_GROUP`, `UNEXPLAINED_OUTLIER_LOW`, `UNEXPLAINED_OUTLIER_HIGH` |
| table_name | text | Y | The table holding the affected record |
| record_id | text | Y | Primary key of the affected record |
| employee_id | text | N | Empty for group-level issues |
| expected_decision | text | Y | `RECALCULATE`, `REVERSE_OR_RATIFY`, `REGROUP`, `PROPOSE_INCREASE`, `FLAG_FOR_REVIEW` |
| detail | text | Y | What was injected, in plain words |
