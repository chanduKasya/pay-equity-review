# AI Usage Disclosure

I used one AI tool: **Claude** (Anthropic), in the Claude desktop app. All of
my prompts are in `prompts/prompt_history.md`.

## Summary

I relied on AI heavily. Claude designed the data model with me and wrote
almost all of the code, tests and documentation in this repository. I set up
the repository, ran and checked the results on my own machine, and worked to
understand the design and the code. I am stating this plainly because the
guidelines ask for honest disclosure.

## Who did what, by phase

| Phase | Prompts | AI contribution | My contribution |
|---|---|---|---|
| Planning and technology stack | 1-2 | Proposed the plan, the standard-library stack and the 72-hour schedule | Supplied the brief and both YottaFlex PDFs |
| Repository setup | 3-7 | Gave the commands and diagnosed a failed `git clone` | Created the GitHub repository, ran the commands and made the first commits |
| Design documents | 7-8 | Wrote `assumptions.md` and `data_dictionary.md` | Read both, and asked for a plain-language explanation of the project before any code was written |
| Master tables | 9 | Wrote `config.py`, `io_utils.py`, `master_data.py` and the first `generate.py` | Ran them on my Mac and committed them |
| Core pipeline | 10 | With access to the project folder: wrote the remaining generator stages, review workflow, anomaly injection, detector, evaluator, validator, reproducibility check, exports, tests and documents; ran them; made the commits | Ran the full pipeline on my Mac and compared the output with the README |
| Estimated pay policy | 23 | Wrote `policy_fit.py` (least squares with the standard library), changed the detector to use it, added tests and updated the results | Asked for the change so the detector no longer reads the generator's constants |
| Systemic disparity | 24 | Added the `demographics` table, the injected group pay gap, the `SYSTEMIC_DISPARITY` check, tests, a dashboard page and the documents | Identified that excluding demographics missed the purpose of a pay equity review, and specified the approach: anonymous groups, medians by level, a 5% gap repeated across levels |
| Docker and CI | 25 | Wrote the `Dockerfile`, `.dockerignore` and the GitHub Actions workflow, and documented them | Asked for both so that another person can run and verify the project without setup |
| Dashboard | 17-18 | Wrote `app.py` and checked that every page loads on both datasets | Ran it on my Mac |

Commits made by Claude carry a `Co-Authored-By: Claude` line, so the git
history shows which commits those are.

## Where AI accelerated the work

- Turning a one-page brief into a 14-table data model with keys and rules.
- Writing about 3,500 lines of Python (including comments) and 32 tests in
  one session, and a dashboard the next day.
- Suggesting checks I would not have thought of: mutation tests that damage
  the data to prove the validator can fail, and a test that runs the
  detector with no ground truth present.

## Where I overrode the AI

These are design decisions the AI made that I reversed. Each one can be
checked against the prompt history and the commits.

### 1. The detector was reading the generator's pay formula (prompt 23)

**What the AI built.** The first detector compared each person's pay with an
"expected" value computed from the same constants the generator used to
create the data (`POLICY_BASE_RATIO` and the others in `config.py`). The AI
had noted this in the README as a limitation and listed "estimate the policy
from the data" under future work.

**Why I changed it.** A detector that is handed the formula that produced
the data is not being tested. The outlier scores would say little about how
it behaves on data it does not already understand. I did not want that left
as a footnote.

**What I required.** That `detect.py` estimate the pay policy from the data
with a regression, without importing those constants.

**Result.** `src/policy_fit.py`, and a test that fails if `detect.py` ever
refers to the policy constants again. Precision and recall stayed at 0.958
and 0.977, which is now a meaningful result.

### 2. Demographics were left out of a pay equity review (prompt 24)

**What the AI built.** Assumption D1 excluded gender, ethnicity and every
other demographic attribute, on the grounds that the brief did not name them
and that it kept sensitive-looking data out of a public repository. The
project could therefore only find individuals who were paid oddly.

**Why I changed it.** That is a safe default, but a pay equity review exists
to find systemic gaps between groups. A solution that cannot see groups at
all misses the purpose of the task.

**What I required.** A demographics table with anonymous groups, and a check
that flags a role when one group's median compa-ratio is consistently 5%
lower than the other's.

**Result.** The `demographics` table, the `SYSTEMIC_DISPARITY` finding, and
a rewritten D1. All three injected roles are found and no others are flagged.
The exact meaning of "consistently" (3 or more levels, and 75% of the levels
compared) was worked out by the AI after its first rule produced a false
positive; that detail is recorded in the table below.

### 3. "Run it" depended on the reader's own setup (prompt 25)

**What the AI built.** Run instructions in the README, and tests that had
only ever been run on the AI's side and on my Mac.

**Why I changed it.** The guidelines ask that another person can install,
run and verify the project. Written instructions do not prove that.

**What I required.** A Dockerfile, and a GitHub Actions workflow that runs
the pipeline and the tests on every push.

**Result.** The workflow passes on Python 3.10, 3.12 and 3.13, and I checked
the first run myself. The Docker image has been written but not yet built.

## Where AI output was wrong and how it was caught

These were caught by the project's own checks during the build:

| Problem | How it was caught | Fix |
|---|---|---|
| The first validator crashed on a broken foreign key instead of reporting it | A mutation test | Join-based checks now stop cleanly when key checks fail |
| The 500-employee dataset had no proposal in SUBMITTED status | The validator's coverage check | Proposal progress changed from a random roll to a fixed pattern |
| The first thresholds produced proposals for about 18% of employees | Reading the row counts | Proposal threshold changed from 0.04 to 0.05 |
| The first test of the estimated policy used tolerances that only held on the 5,000-employee data | The test failed on the 500-employee dataset | The test now checks the total tenure effect with tolerances suited to a small sample |
| The first systemic rule flagged a fourth role that had no injected gap | The evaluation table showed one extra finding | The rule now needs the gap at 75% of the levels compared; checked on 8 seeds |
| Adding the systemic gap bent the estimated pay policy and broke the threshold sweep | The policy comparison and sweep tables | People in a systemic finding are excluded from both |
| The README stated the wrong Python version for my Mac | An error message from my own terminal | Corrected to 3.15 |

## Personal verification log

Checks I ran myself, on my own machine:

| Date | What I checked | Result |
|---|---|---|
| 2026-11-10 | Ran the stage 1 generator on my Mac | 40 roles, 5 levels, 8 locations, 15 FX rates, 4,800 bands, 200 role/level combinations |
| 2026-11-10 | Ran `python3 src/run_all.py --scale full` on my Mac (M1, Python 3.15) | 101 of 101 checks passed, same evaluation table as the README, and 32 of 32 files matched the saved checksums |
| 2026-11-11 | Ran the Streamlit dashboard on my Mac | The Overview page loaded with the same figures as the README |
| 2026-11-11 | Checked the first GitHub Actions run after pushing | All three jobs (Python 3.10, 3.12, 3.13) passed the starter pipeline and the tests in 24 seconds |
