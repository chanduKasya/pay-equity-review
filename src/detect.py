"""
detect.py - the "detective". It reads ONLY the input tables in
data/<scale>/csv and never opens the ground truth folder.

It recomputes every metric from source records and reports:
  EXPIRED_BAND             salary compared to a band not valid on that date
  FTE_IGNORED              part-time pay compared without dividing by FTE
  FX_CONVERSION_MISSING    pay and band in different currencies, not converted
  RATIO_MISMATCH_OTHER     recorded ratio is wrong for an unknown reason
  UNAPPROVED_ADJUSTMENT    adjustment applied with no APPROVED event
  INCOMPARABLE_GROUP       mixed jobs grouped with no rationale
  UNEXPLAINED_OUTLIER_LOW / _HIGH   pay far from what documented factors predict
  SYSTEMIC_DISPARITY       one demographic group paid less across a role's levels

The expected pay is NOT taken from the generator's formula. It is estimated
from the data by a regression (see policy_fit.py).

Run:  python3 src/detect.py --scale starter
"""

import argparse
import os

import config
import io_utils
import lookups
import metrics
import policy_fit
import review

ACTION = {
    "EXPIRED_BAND": "RECALCULATE",
    "FTE_IGNORED": "RECALCULATE",
    "FX_CONVERSION_MISSING": "RECALCULATE",
    "RATIO_MISMATCH_OTHER": "RECALCULATE",
    "UNAPPROVED_ADJUSTMENT": "REVERSE_OR_RATIFY",
    "INCOMPARABLE_GROUP": "REGROUP",
    "UNEXPLAINED_OUTLIER_LOW": "PROPOSE_INCREASE",
    "UNEXPLAINED_OUTLIER_HIGH": "FLAG_FOR_REVIEW",
    "SYSTEMIC_DISPARITY": "GROUP_PAY_REVIEW",
}

BASIS_ORDER = {"ROLE_LEVEL_LOCATION": 1, "ROLE_LEVEL": 2, "FAMILY_LEVEL": 3, "CUSTOM": 4}


def add_finding(findings, issue_type, table_name, record_id, employee_id, evidence):
    findings.append({
        "finding_id": "FND-" + str(len(findings) + 1).zfill(6),
        "issue_type": issue_type,
        "table_name": table_name,
        "record_id": record_id,
        "employee_id": employee_id,
        "recommended_action": ACTION[issue_type],
        "evidence": evidence,
    })


def check_salary_records(tables, band_lookup, rate_lookup, findings):
    """Recompute each record's compa-ratio and compare with the recorded one."""
    band_by_id = lookups.index_by(tables["compensation_band"], "band_id")

    for record in tables["salary_record"]:
        used_band = band_by_id[record["band_id"]]
        correct_band = metrics.find_band_for_date(record["role_id"], record["level_id"],
                                                  record["location_id"], record["effective_date"],
                                                  band_lookup)
        recorded = float(record["recorded_compa_ratio"])
        correct = metrics.compa_ratio(record, correct_band, rate_lookup)

        # Check 1: was the band valid on the salary's effective date?
        date_is_covered = used_band["effective_from"] <= record["effective_date"] <= used_band["effective_to"]
        if not date_is_covered:
            add_finding(findings, "EXPIRED_BAND", "salary_record", record["salary_record_id"],
                        record["employee_id"],
                        "Effective " + record["effective_date"] + " but band " + used_band["band_id"]
                        + " is valid " + used_band["effective_from"] + " to " + used_band["effective_to"]
                        + ". Correct band " + correct_band["band_id"] + " gives "
                        + format(correct, ".4f") + ", recorded " + format(recorded, ".4f"))
            continue

        # Check 2: does the recorded ratio match the recomputed one?
        if abs(recorded - correct) <= config.RATIO_TOLERANCE:
            continue

        # It does not match. Try the two known mistakes to explain why.
        as_if_full_time = dict(record)
        as_if_full_time["fte"] = "1.00"
        ratio_without_fte = metrics.compa_ratio(as_if_full_time, correct_band, rate_lookup)
        ratio_without_fx = round(float(record["annual_amount"]) / float(record["fte"])
                                 / float(correct_band["band_mid"]), 4)
        different_currency = record["currency_code"] != correct_band["currency_code"]

        if float(record["fte"]) < 1.0 and abs(recorded - ratio_without_fte) <= config.RATIO_TOLERANCE:
            issue_type = "FTE_IGNORED"
            reason = "matches the ratio computed without dividing by FTE " + record["fte"]
        elif different_currency and abs(recorded - ratio_without_fx) <= config.RATIO_TOLERANCE:
            issue_type = "FX_CONVERSION_MISSING"
            reason = ("matches " + record["currency_code"] + " pay divided by a "
                      + correct_band["currency_code"] + " midpoint with no conversion")
        else:
            issue_type = "RATIO_MISMATCH_OTHER"
            reason = "does not match any known calculation mistake"
        add_finding(findings, issue_type, "salary_record", record["salary_record_id"],
                    record["employee_id"],
                    "Recorded " + format(recorded, ".4f") + ", recomputed " + format(correct, ".4f")
                    + "; recorded value " + reason)


def check_adjustments(tables, findings):
    """Every ADJUSTMENT salary record needs an APPROVED event before it."""
    events_by_proposal = lookups.group_rows(tables["proposal_event"], "proposal_id")
    for record in tables["salary_record"]:
        if record["change_reason"] != "ADJUSTMENT":
            continue
        approved_date = ""
        trail = []
        for event in events_by_proposal.get(record["proposal_id"], []):
            trail.append(event["to_status"])
            if event["to_status"] == "APPROVED" and event["event_date"] <= record["effective_date"]:
                approved_date = event["event_date"]
        if approved_date == "":
            add_finding(findings, "UNAPPROVED_ADJUSTMENT", "salary_record", record["salary_record_id"],
                        record["employee_id"],
                        "Proposal " + record["proposal_id"] + " trail is " + " > ".join(trail)
                        + " with no APPROVED step before " + record["effective_date"])


def check_groups(tables, snapshot_by_employee, findings):
    """A group that mixes job families or levels must state a rationale."""
    members_by_group = lookups.group_rows(tables["comparable_group_member"], "group_id")
    for group in tables["comparable_group"]:
        families = set()
        level_ids = set()
        for member in members_by_group.get(group["group_id"], []):
            person = snapshot_by_employee.get(member["employee_id"])
            if person is not None:
                families.add(person["job_family"])
                level_ids.add(person["level_id"])
        is_mixed = len(families) > 1 or len(level_ids) > 1
        if is_mixed and group["rationale"].strip() == "":
            add_finding(findings, "INCOMPARABLE_GROUP", "comparable_group", group["group_id"], "",
                        "Group spans job families " + ", ".join(sorted(families)) + " and levels "
                        + ", ".join(sorted(level_ids)) + " but has no rationale")


def check_systemic(tables, snapshot, findings):
    """Compare the demographic groups inside each role, level by level.

    For one role and one level, take the median compa-ratio of each group.
    The level "shows a gap" when one group's median is at least 5% below the
    other's. A role is flagged when the SAME group is lower at 3 or more of
    its levels, and at 75% or more of the levels that had enough people. One level on its own proves little, because small groups
    differ by chance; the same gap at several levels is a pattern.

    Returns (rows for the gap report, set of employee IDs covered by a finding).
    """
    group_of = {}
    for row in tables["demographics"]:
        group_of[row["employee_id"]] = row["demographic_group"]
    group_names = sorted(set(group_of.values()))

    # (role, level) -> group -> list of compa-ratios
    ratios = {}
    for person in snapshot:
        key = (person["role_id"], person["level_id"])
        group = group_of[person["employee_id"]]
        ratios.setdefault(key, {}).setdefault(group, []).append(person["compa_ratio"])

    gap_rows = []
    lower_levels = {}     # (role, lower group) -> list of texts, one per level with a gap
    compared_levels = {}  # role -> number of levels that had enough people
    if len(group_names) == 2:
        first, second = group_names
        for key in sorted(ratios.keys()):
            role_id, level_id = key
            first_values = ratios[key].get(first, [])
            second_values = ratios[key].get(second, [])
            enough = (len(first_values) >= config.SYSTEMIC_MIN_GROUP_SIZE
                      and len(second_values) >= config.SYSTEMIC_MIN_GROUP_SIZE)
            row = {
                "role_id": role_id, "level_id": level_id,
                "group_1": first, "group_1_count": len(first_values), "group_1_median": "",
                "group_2": second, "group_2_count": len(second_values), "group_2_median": "",
                "gap_pct": "", "lower_group": "", "meets_threshold": "",
            }
            if enough:
                first_median = metrics.median(first_values)
                second_median = metrics.median(second_values)
                # Positive gap: group 2 is lower. Negative: group 1 is lower.
                gap_pct = (first_median - second_median) / first_median * 100.0
                lower = second if gap_pct > 0 else first
                if gap_pct < 0:
                    gap_pct_of_higher = (second_median - first_median) / second_median * 100.0
                else:
                    gap_pct_of_higher = gap_pct
                meets = gap_pct_of_higher >= config.SYSTEMIC_GAP_PCT
                row["group_1_median"] = format(first_median, ".4f")
                row["group_2_median"] = format(second_median, ".4f")
                row["gap_pct"] = format(gap_pct_of_higher, ".2f")
                row["lower_group"] = lower
                row["meets_threshold"] = "YES" if meets else "NO"
                compared_levels[role_id] = compared_levels.get(role_id, 0) + 1
                if meets:
                    text = (level_id + " " + format(gap_pct_of_higher, ".1f") + "% (" + str(len(first_values))
                            + " vs " + str(len(second_values)) + " people)")
                    lower_levels.setdefault((role_id, lower), []).append(text)
            gap_rows.append(row)

    covered = set()
    for key in sorted(lower_levels.keys()):
        role_id, lower = key
        if len(lower_levels[key]) < config.SYSTEMIC_MIN_LEVELS:
            continue
        # "Consistently" also means most of the levels, not just three of many.
        # With 40 roles tested, a few would show three gaps purely by chance.
        if len(lower_levels[key]) < config.SYSTEMIC_MIN_LEVEL_SHARE * compared_levels[role_id]:
            continue
        add_finding(findings, "SYSTEMIC_DISPARITY", "role", role_id, "",
                    lower + " median compa-ratio is at least " + format(config.SYSTEMIC_GAP_PCT, ".0f")
                    + "% below the other group at " + str(len(lower_levels[key])) + " of "
                    + str(compared_levels[role_id]) + " levels compared in role " + role_id + ": "
                    + ", ".join(lower_levels[key]))
        for person in snapshot:
            if person["role_id"] == role_id and group_of[person["employee_id"]] == lower:
                covered.add(person["employee_id"])
    return gap_rows, covered


def narrowest_group(employee_id, groups_of_employee, group_by_id):
    """An employee can be in several groups. Use the most specific one."""
    best = None
    for group_id in groups_of_employee.get(employee_id, []):
        group = group_by_id[group_id]
        if best is None or BASIS_ORDER[group["grouping_basis"]] < BASIS_ORDER[best["grouping_basis"]]:
            best = group
    return best


def check_outliers(tables, snapshot, rate_lookup, findings, covered):
    """Compare each active employee's pay with what the factors predict."""
    group_by_id = lookups.index_by(tables["comparable_group"], "group_id")
    groups_of_employee = {}
    ratio_of = {}
    for person in snapshot:
        ratio_of[person["employee_id"]] = person["compa_ratio"]
    members_by_group = lookups.group_rows(tables["comparable_group_member"], "group_id")
    for member in tables["comparable_group_member"]:
        groups_of_employee.setdefault(member["employee_id"], []).append(member["group_id"])

    metric_rows = []
    for person in snapshot:
        employee_id = person["employee_id"]
        residual = round(person["compa_ratio"] - person["expected_ratio"], 4)

        group = narrowest_group(employee_id, groups_of_employee, group_by_id)
        group_id = ""
        group_median = ""
        group_size = ""
        if group is not None and group["grouping_basis"] != "CUSTOM":
            values = []
            for member in members_by_group[group["group_id"]]:
                if member["employee_id"] in ratio_of:
                    values.append(ratio_of[member["employee_id"]])
            group_id = group["group_id"]
            group_median = format(metrics.median(values), ".4f")
            group_size = len(values)

        # A person inside a flagged systemic gap is reported once, under that
        # group-level finding, and not again as an individual low outlier.
        in_systemic_finding = employee_id in covered
        flag = ""
        if residual < -config.OUTLIER_THRESHOLD and not in_systemic_finding:
            flag = "UNEXPLAINED_OUTLIER_LOW"
        elif residual > config.OUTLIER_THRESHOLD:
            flag = "UNEXPLAINED_OUTLIER_HIGH"

        metric_rows.append({
            "employee_id": employee_id,
            "salary_record_id": person["record"]["salary_record_id"],
            "band_id": person["band"]["band_id"],
            "compa_ratio": format(person["compa_ratio"], ".4f"),
            "band_position": format(metrics.band_position(person["record"], person["band"], rate_lookup), ".4f"),
            "level_tenure_months": person["level_tenure_months"],
            "rating": person["rating"],
            "premium_pct": format(person["premium_pct"], ".0f"),
            "expected_compa_ratio": format(person["expected_ratio"], ".4f"),
            "residual": format(residual, ".4f"),
            "group_id": group_id,
            "group_size": group_size,
            "group_median_compa_ratio": group_median,
            "outlier_flag": flag,
            "in_systemic_finding": "YES" if in_systemic_finding else "",
        })

        if flag != "":
            add_finding(findings, flag, "salary_record", person["record"]["salary_record_id"], employee_id,
                        "Compa-ratio " + format(person["compa_ratio"], ".4f") + " vs expected "
                        + format(person["expected_ratio"], ".4f") + " (difference " + format(residual, "+.4f")
                        + ") from level tenure " + str(person["level_tenure_months"]) + " months, rating "
                        + str(person["rating"]) + ", premium " + format(person["premium_pct"], ".0f")
                        + "%. Group " + str(group_id) + " median " + str(group_median)
                        + " over " + str(group_size) + " employees. No evidence record explains the gap")
    return metric_rows


def run_detection(csv_folder):
    tables = io_utils.read_all_tables(csv_folder)
    band_lookup = metrics.build_band_lookup(tables["compensation_band"])
    rate_lookup = metrics.build_rate_lookup(tables["fx_rate"])
    snapshot = review.build_review_snapshot(tables["employee"], tables["salary_record"],
                                            tables["performance_evidence"], tables["tenure"],
                                            tables["role"], band_lookup, rate_lookup)
    snapshot_by_employee = lookups.index_by(snapshot, "employee_id")

    # The detector does not use the generator's pay formula. It estimates the
    # policy from the employees' own data, then replaces the expected ratio
    # on every person with the estimated one.
    #
    # The group comparison runs first because it needs only compa-ratios.
    # People inside a flagged systemic gap are left out of the estimate:
    # their pay does not follow the normal policy, so including them would
    # bend the line.
    findings = []
    gap_rows, covered = check_systemic(tables, snapshot, findings)
    systemic_findings = findings
    people_for_fit = []
    for person in snapshot:
        if person["employee_id"] not in covered:
            people_for_fit.append(person)
    policy = policy_fit.fit_policy(people_for_fit)
    for person in snapshot:
        person["expected_ratio"] = policy_fit.expected_ratio(
            policy, person["level_tenure_months"], person["rating"], person["premium_pct"])

    findings = []
    check_salary_records(tables, band_lookup, rate_lookup, findings)
    check_adjustments(tables, findings)
    check_groups(tables, snapshot_by_employee, findings)
    for finding in systemic_findings:
        add_finding(findings, finding["issue_type"], finding["table_name"], finding["record_id"],
                    finding["employee_id"], finding["evidence"])
    metric_rows = check_outliers(tables, snapshot, rate_lookup, findings, covered)
    return findings, metric_rows, policy, gap_rows


FINDING_COLUMNS = ["finding_id", "issue_type", "table_name", "record_id", "employee_id",
                   "recommended_action", "evidence"]
METRIC_COLUMNS = ["employee_id", "salary_record_id", "band_id", "compa_ratio", "band_position",
                  "level_tenure_months", "rating", "premium_pct", "expected_compa_ratio", "residual",
                  "group_id", "group_size", "group_median_compa_ratio", "outlier_flag",
                  "in_systemic_finding"]
GAP_COLUMNS = ["role_id", "level_id", "group_1", "group_1_count", "group_1_median",
               "group_2", "group_2_count", "group_2_median", "gap_pct", "lower_group", "meets_threshold"]


ESTIMATE_COLUMNS = ["base_ratio", "per_tenure_year", "tenure_cap_years", "per_rating_point",
                  "per_premium_unit", "typical_distance", "people_used", "people_total"]


def main():
    parser = argparse.ArgumentParser(description="Detect pay anomalies from the input tables only.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    csv_folder = os.path.join(args.data, args.scale, "csv")
    out_folder = os.path.join(args.out, args.scale)
    findings, metric_rows, policy, gap_rows = run_detection(csv_folder)
    io_utils.write_csv(findings, out_folder, "findings.csv", FINDING_COLUMNS)
    io_utils.write_csv(metric_rows, out_folder, "employee_metrics.csv", METRIC_COLUMNS)
    io_utils.write_csv(gap_rows, out_folder, "group_gap_by_role_level.csv", GAP_COLUMNS)
    policy_rows = []
    for name in ESTIMATE_COLUMNS:
        policy_rows.append({"parameter": name, "estimated_value": format(policy[name], ".4f")})
    io_utils.write_csv(policy_rows, out_folder, "estimated_policy.csv", ["parameter", "estimated_value"])

    counts = {}
    for finding in findings:
        counts[finding["issue_type"]] = counts.get(finding["issue_type"], 0) + 1
    print("Detection finished:", len(findings), "findings from", csv_folder)
    for issue_type in sorted(counts.keys()):
        print("  " + issue_type.ljust(28) + str(counts[issue_type]).rjust(6))
    print("Estimated pay policy: base", format(policy["base_ratio"], ".4f"),
          "| per year in level", format(policy["per_tenure_year"], ".4f"),
          "(cap", policy["tenure_cap_years"], "years)",
          "| per rating point", format(policy["per_rating_point"], ".4f"),
          "| per unit of premium", format(policy["per_premium_unit"], ".4f"))
    print("Written to", out_folder)


if __name__ == "__main__":
    main()
