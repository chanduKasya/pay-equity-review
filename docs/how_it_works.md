# How It Works: a plain-language tour of the code

Read the files in this order. Each one is short and does one job.

## The idea

It is a treasure hunt that the program sets up and then solves:

1. Build a pretend company (`generate.py`).
2. Hide known mistakes in it and write them on an answer sheet (`inject.py`).
3. Search for mistakes without looking at the answer sheet (`detect.py`).
4. Mark the search against the answer sheet (`evaluate.py`).

## Three terms

- **Band:** the fair pay range for one job in one city in one year, with a
  minimum, a midpoint and a maximum.
- **FTE:** how much of a full week someone works. 1.0 is full-time.
- **Compa-ratio:** pay divided by the band midpoint, after scaling pay to
  full-time and converting it to the band's currency. 1.0 means exactly mid.

Worked example: someone works half-time (FTE 0.5) and is paid 4,300,000 INR.
Their band midpoint is 100,000 USD and 1 USD = 86 INR.

```
full-time pay  = 4,300,000 / 0.5      = 8,600,000 INR
in band money  = 8,600,000 / 86       = 100,000 USD
compa-ratio    = 100,000 / 100,000    = 1.00
```

Skip the FTE step and you get 0.50. Skip the currency step and you get 86.
Those are two of the mistakes the detector looks for.

## Files, in reading order

| File | Job |
|---|---|
| `config.py` | Every number in one place: seed, dates, shares, pay policy, thresholds, anomaly counts |
| `schema.py` | The list of tables with their columns, primary keys and foreign keys |
| `rand_utils.py` | Seeded random helpers: pick one, pick by weight, shuffle |
| `date_utils.py` | Add days, months between two dates |
| `metrics.py` | The formulas: find the band for a date, convert currency, compa-ratio, band position, expected ratio |
| `master_data.py` | Fixed tables: 40 roles, 5 levels, 8 locations, exchange rates, 4,800 bands |
| `employees.py` | The employee table, each person's starting job, and their anonymous demographic group |
| `history.py` | Each employee's salary records, promotions, ratings and tenure |
| `lookups.py` | "Latest salary / latest rating for each employee" helpers |
| `review.py` | Comparable groups, adjustment proposals and the approval trail |
| `inject.py` | Adds the labelled edge cases and builds the ground truth |
| `io_utils.py` | Writes CSV, JSON and SQL, and computes checksums |
| `generate.py` | Calls the stages in order and writes everything |
| `policy_fit.py` | Estimates the pay rule from the data with a least-squares regression |
| `detect.py` | Finds problems using only the input tables |
| `evaluate.py` | Precision and recall against the ground truth |
| `validate.py` | 106 data-quality checks |
| `reproduce.py` | Generates twice and compares checksums |
| `run_all.py` | Runs the five commands in order |

## How one employee's history is built (`history.py`)

1. Draw the employee's random traits once: a small personal pay variation,
   whether they have a critical-skill premium, whether they are a deliberate
   outlier, whether they go part-time, whether they relocate.
2. Write the first salary record: `HIRE` if they joined in 2024 or later,
   otherwise `OPENING_BALANCE` on 2024-01-01.
3. List their dated events for 2024 to 2026: a rating each 15 March, an
   annual review each 1 April, a promotion check each 1 July, and possibly a
   part-time change or a relocation.
4. Sort the events by date and walk through them. Each pay change **adds**
   a salary record. Nothing is ever edited.

Pay at each step comes from the written policy:

```
expected ratio = 0.90
               + 0.02 for each year in the level (up to 5 years)
               + 0.03 for each rating point above 3 (minus below 3)
               + any documented premium
salary = band midpoint x (expected ratio + personal variation)
```

For a deliberate outlier the salary is then multiplied by 0.80 to 0.92
(low) or 1.08 to 1.22 (high).

## How the review works (`review.py`)

1. For each active employee, take the latest salary record and compute the
   correct compa-ratio.
2. Put people in groups: same role, level and location. If fewer than 5,
   widen to role and level; if still fewer than 5, to job family and level.
   Widened groups record why.
3. If someone's ratio is more than 0.05 below the expected ratio, create a
   proposal to bring them up to it, capped at the band maximum.
4. Move the proposal through its steps and save each step as an event:

```
DRAFT -> SUBMITTED -> HR_REVIEWED -> APPROVED -> APPLIED
              |             |
              v             v
          REJECTED      REJECTED
   (rating 2 or lower)  (increase above 20%)
```

5. An APPLIED proposal adds a new salary record with reason `ADJUSTMENT`.

## How the edge cases are hidden (`inject.py`)

| Edge case | The single change that is made |
|---|---|
| Expired band | The record's `band_id` is pointed at last year's band and the recorded ratio recomputed against it |
| FTE ignored | The recorded ratio is recomputed without dividing by FTE |
| Currency conversion missing | The recorded ratio is recomputed without converting currency |
| Unapproved adjustment | A proposal waiting at HR_REVIEWED gets an APPLIED event and a salary record, with no APPROVED step |
| Incomparable group | A custom group is built from two job families with an empty rationale |

Each change writes one row to the ground truth at the same moment.

## How the detector finds them (`detect.py`)

- **Expired band:** is the salary's date inside the band's valid dates?
- **Wrong ratio:** recompute the ratio. If it differs from the recorded one,
  try "what if FTE was skipped?" and "what if conversion was skipped?" to
  name the cause.
- **Unapproved adjustment:** does the adjustment's proposal have an APPROVED
  event dated on or before it?
- **Incomparable group:** do members span more than one job family or
  level while the rationale is empty?
- **Unexplained outlier:** is the ratio more than 0.08 from the expected
  ratio? The finding lists the factors and the group median as evidence.

## How the detector learns the pay rule (`policy_fit.py`)

The detector is not told the pay rule. It works it out from the employees.

Picture a scatter of dots, one per employee: how long they have been in
their level along the bottom, their compa-ratio up the side. The dots form
a rising cloud. **Least squares** draws the straight line through the
cloud that is, overall, closest to all the dots. The slope of that line is
"how much each extra year adds". Doing this for tenure, rating and premium
at once gives four numbers: a starting value and one slope per factor.

Three extra steps:

1. **Finding the cap.** Tenure stops counting after some number of years,
   but the detector does not know how many. It tries 2, 3, 4 ... 10 and
   keeps the one whose line fits best.
2. **Ignoring the troublemakers.** A few badly paid people would tilt the
   line. So it fits once, sets aside the dots furthest from the line, and
   fits again on the rest.
3. **Predicting.** Each person's expected ratio is read off the final line.

On the full dataset it estimates 0.892 + 0.0186 per year (up to 6 years)
+ 0.0277 per rating point. The generator used 0.90, 0.02 (up to 5 years)
and 0.03. Close, and found without being told.

## How systemic disparity is found (`check_systemic` in `detect.py`)

An individual outlier is one person paid oddly. A systemic disparity is a
whole group paid less, where each person might look only slightly low.

Every employee has a label, Group A or Group B. The labels are made up and
mean nothing in the real world. In 3 roles the generator pays Group B 10%
less at every level.

The detector looks at one role at a time:

1. For each level in the role, find the middle (median) compa-ratio of
   Group A and of Group B.
2. If one group's median is at least 5% lower, that level "shows a gap".
3. If the same group is lower at 3 or more levels, and at 75% or more of
   the levels it could compare, the role is flagged.

Why not flag on one level? Think of tossing a coin 10 times. Getting 7
heads does not mean the coin is unfair. With only about 10 people per
group, medians can differ by 5% through luck. Luck rarely repeats at four
or five levels in a row, so a repeated gap is a real pattern.

People inside a flagged role and group are reported once, under the
systemic finding. They are not listed again as individual outliers.

## How reproducibility works

"Random" numbers come from a generator started with a seed. The same seed
gives the same sequence, so the same data. Nothing reads the clock, rows
are written in a fixed order, and files always use the same line endings.
`reproduce.py` proves it by generating twice and comparing a SHA-256
checksum of every file. A checksum is a fingerprint: if one character in a
file changes, the checksum changes.
