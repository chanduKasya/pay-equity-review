# Design Decisions, Trade-offs, Testing and Limitations

## The problem in one paragraph

A company wants to know whether anyone's pay differs from their peers for no
documented reason. To answer that fairly, pay must first be made comparable:
measured against the band that was valid at the time, scaled to full-time, and
converted to the band's currency. Only then can people in comparable jobs be
compared, with tenure, performance and documented premiums taken into account.
Whatever cannot be explained becomes a finding, and a finding can become an
adjustment proposal that must pass through an auditable approval trail.

## Pipeline

```
master tables -> employees -> salary history -> tenure -> review workflow
     -> inject labelled edge cases -> write CSV / JSON / SQL + ground truth
                                                  |
               validate <-------------------------+
               detect (inputs only) -> evaluate (inputs + ground truth)
               reproduce (generate twice, compare checksums)
```

## Key decisions and their trade-offs

| Decision | Why | What it costs |
|---|---|---|
| Standard library only, no pandas | Nothing to install, so the project runs on any Python 3.10+ | More lines of code for grouping and joins |
| Plain lists of dictionaries and simple loops | I can read and explain every line | Slower than a dataframe, though 5,000 employees still take about one second |
| One `schema.py` describing every table | CSV, JSON, SQL and the validator cannot drift apart | One more file to understand first |
| One `config.py` for every number | Thresholds and shares are visible and easy to change | None worth noting |
| A separate random stream per stage | Changing one stage does not shift the random numbers of the others | Slightly more setup |
| Random helpers built only on `rng.random()` | Python guarantees this sequence is stable across versions, so checksums match on any machine | A few lines of custom code instead of `random.choice` |
| Salary records are append-only events | History is never overwritten; an adjustment adds a new record | "Current salary" needs a lookup of the latest record |
| The job (role, level, location) lives on the salary record | No separate assignment-history table | A job change without a pay change cannot be represented |
| `recorded_compa_ratio` as an upstream value | Three edge cases can live in one field without corrupting other rows | It is an extra, slightly artificial column |
| Labels only in `ground_truth/` | The detector cannot cheat | The validator must read both folders |
| Valid data first, anomalies injected afterwards | Baseline and anomalies are separate steps, and each anomaly is exactly one change | Injection code must know the data model well |
| Proposal progress uses a fixed repeating pattern | Every lifecycle state appears even with 500 employees | Less "natural" than a random draw |
| Groups widen from role/level/location to role/level to family/level | Small groups cannot support a comparison | Wider groups are less alike, so the rationale is recorded |

## Where labels come from

The brief says labels must come from documented rules, not random assignment.

- The pay policy is a written formula (`metrics.expected_compa_ratio`).
- Normal pay is that formula plus a small variation.
- An outlier is created by multiplying an employee's pay by a factor well
  outside that variation. The random part is only *who* is chosen. The label
  follows from what was done to the record.
- The same holds for the five edge cases: each label is written by the same
  code, at the same moment, that makes the change.
- Proposal decisions (approve, reject, who approves) are fixed rules based on
  the rating and the size of the increase.

## Testing approach: how I know it works

1. **Hand-calculated unit tests** (`tests/test_metrics.py`). Each formula is
   checked against numbers worked out by hand, including FTE and currency
   together and the band boundaries.
2. **Validation on every run** (`src/validate.py`). 101 checks. Rules that
   the edge cases break on purpose are checked in both directions: every
   broken record must be labelled, and every label must sit on a broken record.
3. **Mutation tests** (`tests/test_pipeline.py`). A copy of the data is
   damaged deliberately and the validator must fail. The first version of
   the validator crashed on a broken foreign key instead of reporting it.
   This test found that, and the validator now stops cleanly.
4. **Isolation test.** The detector is run in a folder that has no ground
   truth at all, which proves it does not depend on the labels.
5. **Negative control.** Custom groups that are mixed but have a rationale
   must not be flagged.
6. **SQL round trip.** The SQL seed is loaded into SQLite; row counts must
   match the CSVs and the database's own foreign-key check must be clean.
7. **Reproducibility.** Two same-seed runs must give identical checksums,
   and must also match the checksums stored with the committed dataset.

## Problems found during the build

| Problem | How it was found | Fix |
|---|---|---|
| Validator crashed on a broken foreign key | Mutation test | Join-based checks are skipped, with a clear message, when key checks fail |
| The 500-employee dataset had no proposal in SUBMITTED status | Coverage check in the validator | Proposal progress changed from a random roll to a fixed pattern |
| About 18% of employees were getting proposals | Reading the row counts | Proposal threshold raised from 0.04 to 0.05, giving about 9% |
| JSON export was 3 times larger than needed | Checking folder sizes | One row per line instead of indented |

## Limitations

- **Shared formulas.** The generator and detector use the same functions in
  `metrics.py`. That guarantees one definition of each formula, but it means
  the rule-based edge cases are detected perfectly by construction.
- **Known policy.** The outlier check compares pay with a policy that is
  written down. A real review would need to estimate it, for example with a
  regression inside each comparable group.
- **Current factors only.** Pay that was fair under an earlier rating is
  flagged once the rating drops. These are the 14 false positives.
- **Snapshot tenure.** Expected pay uses tenure on the review date, while
  pay was set a few months earlier. The difference is at most about 0.013.
- **One label per record.** Real data can have several problems on one record.
- **Scope.** Base salary only, one review cycle, yearly synthetic exchange
  rates, no protected attributes.
- **Starter dataset mix.** The first 200 employees are assigned one to each
  role/level combination, so senior levels are over-represented at 500.
- **Not checked on Windows.**

## What I would do next

- Estimate the pay policy from the data instead of reading it from config.
- Add rating history as an explaining factor to remove the false positives.
- Allow several labelled issues on one record.
- Add a small dashboard over `output/`.
