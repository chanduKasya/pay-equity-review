"""
evaluate.py - marks the detector's findings against the ground truth.

This is the only analysis step that reads the ground truth folder.

For each issue type:
  true positive  (TP): labelled and found
  false positive (FP): found but not labelled
  false negative (FN): labelled but not found
  precision = TP / (TP + FP)   "of what we flagged, how much was right"
  recall    = TP / (TP + FN)   "of what was hidden, how much we found"
  F1        = balance of the two

Run:  python3 src/evaluate.py --scale starter
"""

import argparse
import os

import config
import io_utils


def safe_divide(top, bottom):
    if bottom == 0:
        return 0.0
    return top / float(bottom)


def score(found_keys, truth_keys):
    true_positive = len(found_keys & truth_keys)
    false_positive = len(found_keys - truth_keys)
    false_negative = len(truth_keys - found_keys)
    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    f1 = safe_divide(2 * precision * recall, precision + recall)
    return true_positive, false_positive, false_negative, precision, recall, f1


def run_evaluation(findings, ground_truth, metric_rows):
    issue_types = set()
    found = set()
    truth = set()
    action_of = {}
    for finding in findings:
        key = (finding["issue_type"], finding["record_id"])
        found.add(key)
        action_of[key] = finding["recommended_action"]
        issue_types.add(finding["issue_type"])
    decision_of = {}
    for label in ground_truth:
        key = (label["issue_type"], label["record_id"])
        truth.add(key)
        decision_of[key] = label["expected_decision"]
        issue_types.add(label["issue_type"])

    rows = []
    for issue_type in sorted(issue_types):
        found_here = set()
        truth_here = set()
        for key in found:
            if key[0] == issue_type:
                found_here.add(key)
        for key in truth:
            if key[0] == issue_type:
                truth_here.add(key)
        rows.append(make_row(issue_type, len(truth_here), len(found_here), score(found_here, truth_here)))
    rows.append(make_row("ALL", len(truth), len(found), score(found, truth)))

    # Did the recommended action match the expected decision?
    matched = found & truth
    correct_decisions = 0
    for key in matched:
        if action_of[key] == decision_of[key]:
            correct_decisions = correct_decisions + 1

    misses = []
    for key in sorted(truth - found):
        misses.append({"kind": "MISSED (false negative)", "issue_type": key[0], "record_id": key[1]})
    for key in sorted(found - truth):
        misses.append({"kind": "EXTRA (false positive)", "issue_type": key[0], "record_id": key[1]})

    sweep = threshold_sweep(metric_rows, ground_truth)
    return rows, misses, len(matched), correct_decisions, sweep


def make_row(issue_type, labelled, flagged, result):
    return {
        "issue_type": issue_type,
        "labelled": labelled,
        "flagged": flagged,
        "true_positive": result[0],
        "false_positive": result[1],
        "false_negative": result[2],
        "precision": format(result[3], ".3f"),
        "recall": format(result[4], ".3f"),
        "f1": format(result[5], ".3f"),
    }


def threshold_sweep(metric_rows, ground_truth):
    """How outlier precision and recall change as the threshold moves."""
    truth_records = set()
    for label in ground_truth:
        if label["issue_type"].startswith("UNEXPLAINED_OUTLIER"):
            truth_records.add(label["record_id"])
    sweep = []
    for threshold in [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12]:
        flagged = set()
        for row in metric_rows:
            # Same rule as the detector: a person inside a systemic finding
            # is not also counted as an individual low outlier.
            if row.get("in_systemic_finding", "") == "YES" and float(row["residual"]) < 0:
                continue
            if abs(float(row["residual"])) > threshold:
                flagged.add(row["salary_record_id"])
        result = score(flagged, truth_records)
        sweep.append({
            "threshold": format(threshold, ".2f"),
            "flagged": len(flagged),
            "precision": format(result[3], ".3f"),
            "recall": format(result[4], ".3f"),
            "f1": format(result[5], ".3f"),
        })
    return sweep


def markdown_table(rows, columns):
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        cells = []
        for column in columns:
            cells.append(str(row[column]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


EVALUATION_COLUMNS = ["issue_type", "labelled", "flagged", "true_positive", "false_positive",
                      "false_negative", "precision", "recall", "f1"]
SWEEP_COLUMNS = ["threshold", "flagged", "precision", "recall", "f1"]


def main():
    parser = argparse.ArgumentParser(description="Score the findings against the ground truth.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--truth", default="ground_truth")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    out_folder = os.path.join(args.out, args.scale)
    findings = io_utils.read_csv(os.path.join(out_folder, "findings.csv"))
    metric_rows = io_utils.read_csv(os.path.join(out_folder, "employee_metrics.csv"))
    ground_truth = io_utils.read_csv(os.path.join(args.truth, args.scale, "ground_truth.csv"))

    rows, misses, matched, correct_decisions, sweep = run_evaluation(findings, ground_truth, metric_rows)
    io_utils.write_csv(rows, out_folder, "evaluation.csv", EVALUATION_COLUMNS)
    io_utils.write_csv(misses, out_folder, "evaluation_misses.csv", ["kind", "issue_type", "record_id"])
    io_utils.write_csv(sweep, out_folder, "outlier_threshold_sweep.csv", SWEEP_COLUMNS)

    text = "# Evaluation (" + args.scale + ")\n\n"
    text = text + markdown_table(rows, EVALUATION_COLUMNS) + "\n\n"
    text = text + "Recommended action matched the expected decision for " + str(correct_decisions)
    text = text + " of " + str(matched) + " correctly found issues.\n\n"
    policy_path = os.path.join(out_folder, "estimated_policy.csv")
    if os.path.exists(policy_path):
        estimated = {}
        for row in io_utils.read_csv(policy_path):
            estimated[row["parameter"]] = row["estimated_value"]
        documented = [
            ("base_ratio", "Ratio with no tenure and a rating of 3", config.POLICY_BASE_RATIO),
            ("per_tenure_year", "Added per year in level", config.POLICY_PER_TENURE_YEAR),
            ("tenure_cap_years", "Years after which tenure stops counting", config.POLICY_TENURE_CAP_YEARS),
            ("per_rating_point", "Added per rating point", config.POLICY_PER_RATING_POINT),
            ("per_premium_unit", "Added per unit of documented premium", 1.0),
        ]
        comparison = []
        for name, meaning, true_value in documented:
            comparison.append({"parameter": meaning, "estimated_by_detector": estimated[name],
                               "used_by_generator": format(true_value, ".4f")})
        io_utils.write_csv(comparison, out_folder, "policy_comparison.csv",
                           ["parameter", "estimated_by_detector", "used_by_generator"])
        text = text + "## Pay policy: estimated from data against the generator's values\n\n"
        text = text + "The detector never sees the right-hand column. It is shown here only to check the estimate.\n\n"
        text = text + markdown_table(comparison, ["parameter", "estimated_by_detector", "used_by_generator"]) + "\n\n"
    text = text + "## Outlier threshold sweep\n\n"
    text = text + "Current threshold: " + format(config.OUTLIER_THRESHOLD, ".2f") + "\n\n"
    text = text + markdown_table(sweep, SWEEP_COLUMNS) + "\n"
    io_utils.write_text(os.path.join(out_folder, "evaluation.md"), text)

    print("Evaluation (" + args.scale + ")")
    print("  " + "issue type".ljust(28) + "label  flag    TP    FP    FN   prec recall     f1")
    for row in rows:
        print("  " + row["issue_type"].ljust(28) + str(row["labelled"]).rjust(5) + str(row["flagged"]).rjust(6)
              + str(row["true_positive"]).rjust(6) + str(row["false_positive"]).rjust(6)
              + str(row["false_negative"]).rjust(6) + row["precision"].rjust(7)
              + row["recall"].rjust(7) + row["f1"].rjust(7))
    print("  Decisions matched:", correct_decisions, "of", matched)
    print("Written to", out_folder)


if __name__ == "__main__":
    main()
