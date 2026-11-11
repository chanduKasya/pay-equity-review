# Pay Equity Review: synthetic data generator and anomaly detector

Candidate project for the YottaFlex AI recruitment drive.

**The task:** compare compensation against role, level, location and documented
factors to identify unexplained disparities, on synthetic data that I generate.

**What this repository does:**

1. **Generates** a synthetic company: 5,000 employees, 200 role/level
   combinations, 8 locations in 5 currencies and 3 years of salary history,
   with promotions, part-time changes and currency changes.
2. **Runs the review workflow:** effective-dated bands, FTE and currency
   normalisation, compa-ratio and band position, comparable groups, and
   adjustment proposals with evidence and an approval trail.
3. **Injects labelled edge cases** and stores the labels in a separate
   ground truth folder.
4. **Detects** the problems using only the input tables.
5. **Validates and evaluates:** 101 data-quality checks, precision and recall
   against the ground truth, and a same-seed reproducibility check.

Everything is fully synthetic. No external or personal data is used.

## Quick start

Requirements: Python 3.10 or newer. Nothing to install: the project uses only
the Python standard library.

```
git clone https://github.com/chanduKasya/pay-equity-review.git
cd pay-equity-review
python3 src/run_all.py --scale starter
```

`starter` builds 500 employees in under a second. For the full 5,000:

```
python3 src/run_all.py --scale full
```

`run_all.py` runs five steps in order and stops if one fails. Each step can
also be run alone:

| Step | Command | What it does |
|---|---|---|
| 1 | `python3 src/generate.py --scale full --seed 20261022` | Builds every table as CSV, JSON and SQL |
| 2 | `python3 src/validate.py --scale full` | Runs 101 data-quality checks |
| 3 | `python3 src/detect.py --scale full` | Finds anomalies from the input tables only |
| 4 | `python3 src/evaluate.py --scale full` | Scores the findings against the ground truth |
| 5 | `python3 src/reproduce.py --scale full` | Generates twice and compares checksums |

Optional tests (23 tests, about one second):

```
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
python -m pytest
```

The virtual environment is needed on systems where Python is managed by the
operating system or Homebrew, which refuse a plain `pip install`.

## Optional dashboard

A Streamlit app lets you explore the results in a browser: findings with
their evidence, one employee's pay history, the pay distribution, proposals
with their approval trail, the validation report and a compa-ratio calculator.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-app.txt
streamlit run app.py
```

The app only reads the files in `data/`, `output/` and `ground_truth/`. The
core project in `src/` still needs nothing beyond the standard library.

![Dashboard overview](docs/images/dashboard_overview.png)

## How to verify the key behaviour

After `python3 src/run_all.py --scale full` you should see:

- `Validation (full): 101 of 101 checks passed`
- an evaluation table ending in `ALL  259  267  253  14  6  0.948  0.977  0.962`
- `Reproducibility (full): 32 of 32 files identical across two runs`

The same results are saved as files:

| File | Contents |
|---|---|
| `output/full/validation_summary.md` | Every check with pass or fail |
| `output/full/evaluation.md` | Precision, recall and F1 per issue type |
| `output/full/findings.csv` | Each finding with its evidence in plain words |
| `output/full/employee_metrics.csv` | Compa-ratio, band position, expected ratio and group median per employee |
| `output/full/reproducibility.md` | Checksums of both runs, file by file |

## Results (full dataset, seed 20261022)

### Volume

| Table | Rows | | Table | Rows |
|---|---|---|---|---|
| role | 40 | | performance_evidence | 11,791 |
| level | 5 | | promotion | 1,225 |
| location | 8 | | tenure | 5,000 |
| fx_rate | 15 | | comparable_group | 523 |
| compensation_band | 4,800 | | comparable_group_member | 6,657 |
| employee | 5,000 | | adjustment_proposal | 435 |
| salary_record | 18,617 | | proposal_event | 1,704 |

4,590 employees are active and 410 have left. 606 salary records are part-time,
and 80 are paid in a different currency from their band.

### Detection against ground truth

| Issue type | Labelled | Flagged | Found | Extra | Missed | Precision | Recall |
|---|---|---|---|---|---|---|---|
| Salary compared to expired band | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 |
| FTE ignored | 40 | 40 | 40 | 0 | 0 | 1.000 | 1.000 |
| Currency conversion missing | 30 | 30 | 30 | 0 | 0 | 1.000 | 1.000 |
| Adjustment applied without approval | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 |
| Incomparable roles grouped without rationale | 15 | 15 | 15 | 0 | 0 | 1.000 | 1.000 |
| Unexplained outlier, low | 78 | 75 | 75 | 0 | 3 | 1.000 | 0.962 |
| Unexplained outlier, high | 41 | 52 | 38 | 14 | 3 | 0.731 | 0.927 |
| **All** | **259** | **267** | **253** | **14** | **6** | **0.948** | **0.977** |

How to read this honestly:

- The five rule-based edge cases score 100% because each one breaks a rule
  that can be checked exactly. This shows the labels and the data agree. It
  does not show the detector would cope with messier real-world data.
- The outlier rows are the meaningful ones. The 6 misses are injected
  outliers that are too mild to cross the 0.08 threshold.
- All 14 extra "high" flags are the same kind of person: their rating fell
  sharply in 2026, and the no-pay-cut rule kept their salary above what
  their current rating predicts. They were not injected, so they count as
  false positives, but a reviewer would probably want to see them.
- `output/full/outlier_threshold_sweep.csv` shows the trade-off. A threshold
  of 0.07 gives 0.983 recall at 0.830 precision. A threshold of 0.10 gives
  0.972 precision at 0.866 recall.

### Validation

101 of 101 checks pass. They cover primary keys (14), foreign keys (25),
allowed values (11), ID formats (10), date ordering (7), arithmetic
reconciliation (7), lifecycle transitions (3), duplicates (17), ground-truth
separation (3), coverage (2) and exports (2).

The tests also damage a copy of the data on purpose (a broken foreign key, a
duplicate key, a wrong ratio, an illegal status jump) and confirm the validator
fails each time. A validator that always passes proves nothing.

### Reproducibility

Two runs with the same seed give 32 of 32 identical files (SHA-256). A run
with a different seed changes 21 files. The 11 that stay the same are the
fixed master tables and the SQL schema.

## The five required edge cases

| Edge case | How it appears in the data | How it is detected |
|---|---|---|
| Salary compared to expired band | The salary record points at last year's band | The band's dates do not cover the salary's effective date |
| FTE ignored | The recorded compa-ratio was computed on part-time pay | Recomputing with pay divided by FTE gives a different value |
| Currency conversion missing | Pay in one currency was divided by a midpoint in another | Recomputing with conversion gives a different value |
| Adjustment applied without approval | A proposal jumps from HR_REVIEWED to APPLIED | The adjustment's trail has no APPROVED event |
| Incomparable roles grouped without rationale | A custom group mixes job families and gives no rationale | Members span more than one family or level, and the rationale is empty |

Deliberate unexplained outliers are added as well: 2% of active employees
are paid low and 1% high against the documented policy.

## Repository layout

```
src/                 all code (see docs/how_it_works.md for a guided tour)
app.py               optional Streamlit dashboard over the results
tests/               pytest tests
data/<scale>/csv     input tables, one CSV per table
data/<scale>/json    the same tables as JSON
data/<scale>/sql     schema.sql and seed.sql (SQLite-compatible)
data/<scale>/manifest.json   seed, command, row counts, checksums
ground_truth/<scale> labels, kept apart from the inputs on purpose
output/<scale>       findings, metrics, validation, evaluation, reproducibility
docs/                assumptions, data dictionary, design decisions, AI usage
prompts/             every prompt sent to an AI tool
```

## Documents

| Document | What it answers |
|---|---|
| `docs/assumptions.md` | What I assumed where the brief was unclear, and deviations |
| `docs/data_dictionary.md` | Every table, field, key, allowed value and rule |
| `docs/design_decisions.md` | Key decisions, trade-offs, testing approach and limitations |
| `docs/how_it_works.md` | A plain-language tour of the code, file by file |
| `docs/ai_usage.md` | Where AI was used, and what was reviewed and validated |
| `prompts/prompt_history.md` | Every prompt, in order |

## Known limitations

- The detector and the generator share the same formulas, so the rule-based
  edge cases are found perfectly by construction.
- The outlier check uses the written pay policy. A real company would have
  to estimate that relationship from its data.
- The outlier check looks at current factors only, so pay protected by an
  earlier rating is flagged as unexplained.
- Only base salary is modelled. There is one review cycle.
- Exchange rates are made-up yearly values.
- No gender, ethnicity, age or names are generated (see deviation D1).
- For employees hired before 2024, time in level is counted from hire.
- The dashboard is read-only. It shows results and does not edit data or approve proposals.

More detail is in `docs/design_decisions.md`.

## Environment

Run and checked on Python 3.10 and 3.13 on Linux and on Python 3.15 on
macOS (Apple M1). All three produce identical checksums. Data files use `\n` line endings on every
platform.
