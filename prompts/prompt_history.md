# Prompt History

Every prompt I sent to an AI tool for this project. How the AI was used, and
what I reviewed myself, is described in `docs/ai_usage.md`.

**Tool:** Claude (Anthropic), in the Claude desktop app, model Claude Fable 5.2.
This was the only AI tool used. From prompt 10 onward the AI had access to the
project folder on my computer and wrote files, ran the code and made git
commits there. Those commits carry a `Co-Authored-By: Claude` line.

This file has two parts:

1. **Summary by phase**: a short description of what each group of prompts
   asked for and what came out of it. This is a summary, not the original wording.
2. **Full log**: every prompt in order, copied word for word.

## Part 1: Summary by phase

| Phase | Prompts | What I asked for | Outcome |
|---|---|---|---|
| Planning and technology stack | 1-2 | A plan for the YottaFlex candidate project, given the brief and both guideline PDFs, and step-by-step guidance for the 72-hour window | A staged plan, a Python standard-library stack and a schedule |
| Repository setup and troubleshooting | 3-7 | Help with the terminal commands to clone the repository, create the folder structure and make the first commit, including two errors along the way | Working repository with the first commits made by me |
| Design documents and understanding | 7-8 | The assumptions and data dictionary, then a plain-language explanation of the project and both documents before any code | `docs/assumptions.md`, `docs/data_dictionary.md`, and my own understanding of the scope |
| Master tables | 9 | The first generator code for the fixed master tables | `config.py`, `io_utils.py`, `master_data.py`, first `generate.py`; run and committed by me |
| Core pipeline | 10 | For the AI to take over and build the rest: employees, salary history, review workflow, anomaly injection, detector, evaluator, validator, reproducibility check, exports and tests | The remaining code in `src/`, the tests, the datasets and the documents |
| Running and understanding | 11-16 | How to run the project in the terminal and in VS Code, a fix for a `pip` error, a beginner-level explanation of the whole project, and an estimate of the effort without AI | Confirmed run on my Mac with identical checksums; virtual-environment steps added to the README |
| Dashboard | 17-18 | A clean, interactive Streamlit app over the results | `app.py`, running on my Mac |
| Estimated pay policy | 23 | For the detector to estimate the pay policy from the data by regression, not read the generator's constants | `src/policy_fit.py`, updated detector, tests and results |
| Systemic disparity | 24 | A demographics table with anonymous groups, and a detector check that flags a role when one group's median compa-ratio is consistently 5% lower | `demographics` table, `SYSTEMIC_DISPARITY` findings, a group comparison report and dashboard page |
| Housekeeping | 19-22 | A single-file snapshot of the project, and a more professional presentation of this prompt log | A local snapshot file (not in the repository), and this summary section |

## Part 2: Full log

Prompts are copied word for word, including typing mistakes. Where I pasted
terminal output or a screenshot instead of typing a question, the entry
describes what was pasted. AI responses are not included (the FAQ makes them
optional).

**Limitation:** the app has no prompt export, so this log is kept by hand.

All times are IST.

### 2026-11-10

| # | Time | Prompt |
|---|---|---|
| 1 | 11:42 | "this is a task for my job interview make a plan and path  and i am attaching two pdfs go through them , target is to get the job" (attached: the task brief as a text file, the Submission Guidelines PDF and the FAQ PDF) |
| 2 | 11:45 | "they sent me this email like 30 min ago , guide me from start to the end" |
| 3 | 11:47 | "step 1 commands not found in my terminal, i am using mac m1 air" |
| 4 | 11:52 | Pasted terminal output: `git clone` of this repository failed with "Repository not found" |
| 5 | 11:55 | Pasted terminal output: `git clone` succeeded and I had moved into the project folder |
| 6 | 11:59 | Pasted terminal output of `ls -a` showing the new folders and files |
| 7 | 12:01 | "done" |
| 8 | 12:07 | "before continuing tell me about the project , what they asked , what are we doing, etc and tell me whats in assumptions , data dictionary,  like i am 10." |
| 9 | 12:19 | "pushed , and done" |
| 10 | 14:04 | "all done until now , take control , and do everything from now , and teach me what you did at the end" |
| 11 | 14:28 | "how to run it" |
| 12 | 14:29 | Pasted terminal output of `python3 src/run_all.py --scale full` from my Mac |
| 13 | 14:32 | "how to run it on VS code" |
| 14 | 14:44 | Pasted terminal output: `pip3 install pytest` failed with "externally-managed-environment" |
| 15 | 14:48 | "now explain everything i need to know, like i am 10 and a beginner" |
| 16 | 14:53 | "with out any AI help , how long can this project take with one person like me" |

### 2026-11-11

| # | Time | Prompt |
|---|---|---|
| 17 | 11:08 | "design a stream lit app for this project with clean and interactive application" |
| 18 | 12:12 | Sent a screenshot of the dashboard running in my browser, with no text |
| 19 | 12:14 | "put everything until now in a single text file , every file content , every source code and all," |
| 20 | 12:15 | "remove the prompt history" (this referred to the single text file from prompt 19) |
| 21 | 12:23 | "replace the prompts file with this , remove all the unnecessary prompts previously and all the beginner prompts that will look unprofessional, and edit the AI usage file also" followed by my own draft of a shorter, reworded prompt list. The AI advised keeping the word-for-word log and proposed adding a summary by phase instead. |
| 22 | 12:25 | "yes" (agreeing to the summary-by-phase approach, which is Part 1 of this file) |
| 23 | 12:28 | "Update `detect.py` so it estimates the pay policy from the data rather than importing the exact constants from the generator. You can write a simple linear regression using `scikit-learn` (or a basic least-squares math function using standard library Python) to infer the impact of level tenure and rating on compa-ratio." |
| 24 | 12:34 | "`D1` deliberately excluded gender and ethnicity to avoid sensitive data. While this is a safe default, a \"Pay Equity Review\" inherently exists to find systemic bias across protected classes, not just individual random outliers. Generate a new synthetic table for `demographics.csv` with anonymized groups (e.g., `Group A`, `Group B`). Update the detector to calculate the median compa-ratio for each group within the same job level. If Group B's median is consistently 5% lower than Group A's across multiple roles, flag this as `SYSTEMIC_DISPARITY`." |
