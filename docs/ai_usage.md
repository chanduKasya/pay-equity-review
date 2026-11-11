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
| Dashboard | 17-18 | Wrote `app.py` and checked that every page loads on both datasets | Ran it on my Mac |

Commits made by Claude carry a `Co-Authored-By: Claude` line, so the git
history shows which commits those are.

## Where AI accelerated the work

- Turning a one-page brief into a 14-table data model with keys and rules.
- Writing about 3,500 lines of Python (including comments) and 23 tests in
  one session, and a dashboard the next day.
- Suggesting checks I would not have thought of: mutation tests that damage
  the data to prove the validator can fail, and a test that runs the
  detector with no ground truth present.

## Where AI output was wrong and how it was caught

These were caught by the project's own checks during the build:

| Problem | How it was caught | Fix |
|---|---|---|
| The first validator crashed on a broken foreign key instead of reporting it | A mutation test | Join-based checks now stop cleanly when key checks fail |
| The 500-employee dataset had no proposal in SUBMITTED status | The validator's coverage check | Proposal progress changed from a random roll to a fixed pattern |
| The first thresholds produced proposals for about 18% of employees | Reading the row counts | Proposal threshold changed from 0.04 to 0.05 |
| The README stated the wrong Python version for my Mac | An error message from my own terminal | Corrected to 3.15 |

## Personal verification log

Checks I ran myself, on my own machine:

| Date | What I checked | Result |
|---|---|---|
| 2026-11-10 | Ran the stage 1 generator on my Mac | 40 roles, 5 levels, 8 locations, 15 FX rates, 4,800 bands, 200 role/level combinations |
| 2026-11-10 | Ran `python3 src/run_all.py --scale full` on my Mac (M1, Python 3.15) | 101 of 101 checks passed, same evaluation table as the README, and 32 of 32 files matched the saved checksums |
| 2026-11-11 | Ran the Streamlit dashboard on my Mac | The Overview page loaded with the same figures as the README |
