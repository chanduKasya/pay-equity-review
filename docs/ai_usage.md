# AI Usage Disclosure

I used one AI tool: **Claude** (Anthropic), in the Claude desktop app. All of
my prompts are in `prompts/prompt_history.md`.

## Summary

I relied on AI heavily. Claude designed the data model with me, and wrote
almost all of the code, tests and documentation in this repository. I am
stating that plainly because the guidelines ask for honest disclosure.

## Timeline

| Stage | Who did what |
|---|---|
| Planning (prompts 1-2) | I shared the brief and both YottaFlex PDFs. Claude proposed the plan, stack and 72-hour schedule. |
| Repository setup (prompts 3-7) | I created the GitHub repository, ran the setup commands on my Mac and made the first commits. Claude gave the commands and helped when `git clone` failed. |
| Design documents (prompts 7-8) | Claude wrote `assumptions.md` and `data_dictionary.md`. I asked for a plain-language explanation of the project and both documents before going further (prompt 8). |
| Master tables (prompt 9) | Claude wrote `config.py`, `io_utils.py`, `master_data.py` and the first `generate.py`. I ran them on my Mac and committed them. |
| Everything else (prompt 10) | I asked Claude to take over. With access to the project folder, it wrote the remaining generator stages, the review workflow, anomaly injection, detector, evaluator, validator, reproducibility check, exports, tests and documents. It ran them and made the commits. |
| Dashboard (prompt 17) | I asked for a Streamlit app. Claude wrote `app.py`, checked every page loads on both datasets and committed it. |

Commits made by Claude carry a `Co-Authored-By: Claude` line, so the git
history shows which commits those are.

## Where AI accelerated the work

- Turning a one-page brief into a 14-table data model with keys and rules.
- Writing about 3,500 lines of Python (including comments) and 23 tests in one session.
- Thinking of checks I would not have: mutation tests that damage the data
  to prove the validator can fail, and a test that runs the detector with
  no ground truth present.

## Where AI output was wrong and how it was caught

These were caught by the project's own checks during the build:

- The first validator crashed on a broken foreign key instead of reporting
  it. A mutation test exposed this.
- The 500-employee dataset had no proposal in SUBMITTED status. The
  validator's coverage check failed until proposal progress was changed.
- The first thresholds produced proposals for about 18% of employees,
  which is unrealistic. The threshold was changed.

## Personal verification log

Checks I ran myself, on my own machine:

| Date | What I checked | Result |
|---|---|---|
| 2026-11-10 | Ran the stage 1 generator on my Mac | 40 roles, 5 levels, 8 locations, 15 FX rates, 4,800 bands, 200 role/level combinations |
| 2026-11-10 | Ran `python3 src/run_all.py --scale full` on my Mac (M1, Python 3.15) | 101 of 101 checks passed, same evaluation table as the README, and 32 of 32 files matched the saved checksums |
