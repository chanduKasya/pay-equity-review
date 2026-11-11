"""
validate.py - quality checks on a generated dataset.

Groups of checks (as required by the brief):
  primary-key uniqueness, foreign-key integrity, allowed values (enums),
  date ordering, arithmetic reconciliation, lifecycle transitions,
  duplicate checks, ID formats, ground-truth separation, coverage,
  and loading the SQL seed into a real database.

The validator is quality assurance for the DATASET, so it is allowed to read
the ground truth. It uses it for one purpose: to confirm that every broken
rule sits on a labelled record, and that nothing else is broken.

Run:  python3 src/validate.py --scale starter
Exit code is 0 when every check passes, 1 otherwise.
"""

import argparse
import os
import re
import sqlite3
import sys

import config
import date_utils
import io_utils
import lookups
import metrics
import schema

ENUMS = {
    ("location", "currency_code"): ["INR", "USD", "GBP", "EUR", "SGD"],
    ("employee", "employment_status"): ["ACTIVE", "TERMINATED"],
    ("demographics", "demographic_group"): config.DEMOGRAPHIC_GROUPS,
    ("salary_record", "change_reason"): ["OPENING_BALANCE", "HIRE", "ANNUAL_REVIEW", "PROMOTION",
                                          "FTE_CHANGE", "RELOCATION", "ADJUSTMENT"],
    ("salary_record", "fte"): ["0.50", "0.60", "0.80", "1.00"],
    ("performance_evidence", "evidence_type"): ["ANNUAL_RATING", "CRITICAL_SKILL_PREMIUM"],
    ("comparable_group", "grouping_basis"): ["ROLE_LEVEL_LOCATION", "ROLE_LEVEL", "FAMILY_LEVEL", "CUSTOM"],
    ("adjustment_proposal", "status"): ["DRAFT", "SUBMITTED", "HR_REVIEWED", "APPROVED", "REJECTED", "APPLIED"],
    ("proposal_event", "to_status"): ["DRAFT", "SUBMITTED", "HR_REVIEWED", "APPROVED", "REJECTED", "APPLIED"],
    ("proposal_event", "actor_role"): ["MANAGER", "HR_PARTNER", "COMP_COMMITTEE", "SYSTEM"],
}

ID_PATTERNS = {
    ("employee", "employee_id"): r"^EMP-\d{6}$",
    ("compensation_band", "band_id"): r"^BAND-[A-Z]{3,4}-L[1-5]-[A-Z]{3}-20\d{2}$",
    ("salary_record", "salary_record_id"): r"^SAL-EMP-\d{6}-20\d{2}-\d{2}$",
    ("performance_evidence", "evidence_id"): r"^PERF-EMP-\d{6}-20\d{2}-\d{2}$",
    ("promotion", "promotion_id"): r"^PROMO-EMP-\d{6}-\d{2}$",
    ("comparable_group", "group_id"): r"^GRP-2026-\d{6}$",
    ("adjustment_proposal", "proposal_id"): r"^ADJ-2026-\d{6}$",
    ("proposal_event", "event_id"): r"^ADJEVT-2026-\d{6}-\d{2}$",
}

ALLOWED_TRANSITIONS = [
    ("", "DRAFT"), ("DRAFT", "SUBMITTED"), ("SUBMITTED", "HR_REVIEWED"), ("SUBMITTED", "REJECTED"),
    ("HR_REVIEWED", "APPROVED"), ("HR_REVIEWED", "REJECTED"), ("APPROVED", "APPLIED"),
]

LABEL_WORDS = ["issue_type", "ground_truth", "is_anomaly", "anomaly", "label", "expected_decision"]


class Report:
    """Collects the result of each check."""

    def __init__(self):
        self.rows = []

    def add(self, category, name, checked, problems):
        """problems is a list of short texts. An empty list means PASS."""
        if len(problems) == 0:
            status = "PASS"
            example = ""
        else:
            status = "FAIL"
            example = problems[0]
        self.rows.append({
            "category": category,
            "check": name,
            "status": status,
            "records_checked": checked,
            "problems": len(problems),
            "first_problem": example,
        })

    def all_passed(self):
        for row in self.rows:
            if row["status"] != "PASS":
                return False
        return True


def labelled_ids(ground_truth, issue_type):
    ids = set()
    for label in ground_truth:
        if label["issue_type"] == issue_type:
            ids.add(label["record_id"])
    return ids


def check_primary_keys(tables, report):
    for table in schema.TABLES:
        seen = set()
        problems = []
        for row in tables[table["name"]]:
            key = []
            for column in table["pk"]:
                key.append(row[column])
                if row[column] == "":
                    problems.append("empty key column " + column)
            key = tuple(key)
            if key in seen:
                problems.append("duplicate key " + str(key))
            seen.add(key)
        report.add("Primary keys", table["name"] + ": key is unique and not empty",
                   len(tables[table["name"]]), problems)


def check_foreign_keys(tables, report):
    for table in schema.TABLES:
        for column, parent_table, parent_column in table["fks"]:
            parent_values = set()
            for row in tables[parent_table]:
                parent_values.add(row[parent_column])
            problems = []
            checked = 0
            for row in tables[table["name"]]:
                if row[column] == "":
                    continue          # optional relationship, nothing to check
                checked = checked + 1
                if row[column] not in parent_values:
                    problems.append(row[column] + " not found in " + parent_table)
            report.add("Foreign keys", table["name"] + "." + column + " -> " + parent_table + "." + parent_column,
                       checked, problems)


def check_enums(tables, report):
    for key in ENUMS:
        table_name, column = key
        allowed = ENUMS[key]
        problems = []
        for row in tables[table_name]:
            if row[column] not in allowed:
                problems.append("value '" + row[column] + "' is not allowed")
        report.add("Allowed values", table_name + "." + column, len(tables[table_name]), problems)

    problems = []
    checked = 0
    for row in tables["performance_evidence"]:
        checked = checked + 1
        if row["evidence_type"] == "ANNUAL_RATING":
            if row["rating"] not in ["1", "2", "3", "4", "5"] or row["premium_pct"] != "":
                problems.append(row["evidence_id"] + " rating must be 1-5 with no premium")
        else:
            if row["rating"] != "" or not (5 <= float(row["premium_pct"]) <= 20):
                problems.append(row["evidence_id"] + " premium must be 5-20 with no rating")
    report.add("Allowed values", "performance_evidence: rating 1-5 or premium 5-20 by type", checked, problems)

    problems = []
    for row in tables["salary_record"]:
        if int(row["annual_amount"]) <= 0:
            problems.append(row["salary_record_id"] + " amount is not positive")
        if (row["change_reason"] == "ADJUSTMENT") != (row["proposal_id"] != ""):
            problems.append(row["salary_record_id"] + " proposal_id must be set only for ADJUSTMENT")
    report.add("Allowed values", "salary_record: positive amount, proposal only on ADJUSTMENT",
               len(tables["salary_record"]), problems)


def check_id_formats(tables, report):
    for key in ID_PATTERNS:
        table_name, column = key
        pattern = re.compile(ID_PATTERNS[key])
        problems = []
        for row in tables[table_name]:
            if not pattern.match(row[column]):
                problems.append(row[column] + " does not match the ID convention")
        report.add("ID formats", table_name + "." + column, len(tables[table_name]), problems)

    problems = []
    for band in tables["compensation_band"]:
        expected = ("BAND-" + band["role_id"] + "-" + band["level_id"] + "-"
                    + band["location_id"] + "-" + band["band_year"])
        if band["band_id"] != expected:
            problems.append(band["band_id"] + " does not match its own columns")
    report.add("ID formats", "compensation_band: ID parts equal role, level, location, year",
               len(tables["compensation_band"]), problems)

    problems = []
    for record in tables["salary_record"]:
        expected_start = "SAL-" + record["employee_id"] + "-" + record["effective_date"][0:4] + "-"
        if not record["salary_record_id"].startswith(expected_start):
            problems.append(record["salary_record_id"] + " does not match employee and year")
    report.add("ID formats", "salary_record: ID parts equal employee and effective year",
               len(tables["salary_record"]), problems)


def check_dates(tables, ground_truth, report):
    employee_by_id = lookups.index_by(tables["employee"], "employee_id")

    problems = []
    for band in tables["compensation_band"]:
        if not band["effective_from"] < band["effective_to"]:
            problems.append(band["band_id"] + " ends before it starts")
    report.add("Date ordering", "compensation_band: effective_from before effective_to",
               len(tables["compensation_band"]), problems)

    # Bands for the same job must not overlap in time.
    problems = []
    band_lookup = metrics.build_band_lookup(tables["compensation_band"])
    for key in band_lookup:
        ordered = sorted(band_lookup[key], key=lambda band: band["effective_from"])
        for position in range(1, len(ordered)):
            if ordered[position]["effective_from"] <= ordered[position - 1]["effective_to"]:
                problems.append(ordered[position]["band_id"] + " overlaps the previous band")
    report.add("Date ordering", "compensation_band: no overlapping bands for one job",
               len(tables["compensation_band"]), problems)

    problems = []
    for employee in tables["employee"]:
        terminated = employee["employment_status"] == "TERMINATED"
        if terminated != (employee["termination_date"] != ""):
            problems.append(employee["employee_id"] + " status and termination date disagree")
        if terminated and employee["termination_date"] <= employee["hire_date"]:
            problems.append(employee["employee_id"] + " terminated before hire")
        if employee["manager_employee_id"] == employee["employee_id"]:
            problems.append(employee["employee_id"] + " is their own manager")
    report.add("Date ordering", "employee: termination after hire, status consistent",
               len(tables["employee"]), problems)

    # Salary history: first record type, strictly increasing dates, inside employment.
    problems = []
    records_by_employee = lookups.group_rows(tables["salary_record"], "employee_id")
    for employee_id in records_by_employee:
        employee = employee_by_id[employee_id]
        ordered = sorted(records_by_employee[employee_id], key=lambda record: record["effective_date"])
        first = ordered[0]
        if employee["hire_date"] >= config.HISTORY_START:
            if first["change_reason"] != "HIRE" or first["effective_date"] != employee["hire_date"]:
                problems.append(employee_id + " first record must be HIRE on the hire date")
        else:
            if first["change_reason"] != "OPENING_BALANCE" or first["effective_date"] != config.HISTORY_START:
                problems.append(employee_id + " first record must be OPENING_BALANCE on " + config.HISTORY_START)
        for position in range(1, len(ordered)):
            if ordered[position]["effective_date"] <= ordered[position - 1]["effective_date"]:
                problems.append(employee_id + " has two records that are not in increasing date order")
            if ordered[position]["change_reason"] in ["HIRE", "OPENING_BALANCE"]:
                problems.append(employee_id + " has a second starting record")
        for record in ordered:
            if employee["termination_date"] != "" and record["effective_date"] > employee["termination_date"]:
                problems.append(record["salary_record_id"] + " is dated after termination")
    report.add("Date ordering", "salary_record: valid first record, strictly increasing dates",
               len(tables["salary_record"]), problems)

    missing = []
    for employee in tables["employee"]:
        if employee["employee_id"] not in records_by_employee:
            missing.append(employee["employee_id"] + " has no salary record")
    report.add("Date ordering", "employee: every employee has at least one salary record",
               len(tables["employee"]), missing)

    problems = []
    for row in tables["performance_evidence"]:
        if row["evidence_date"] < employee_by_id[row["employee_id"]]["hire_date"]:
            problems.append(row["evidence_id"] + " is dated before hire")
        if row["review_year"] != row["evidence_date"][0:4]:
            problems.append(row["evidence_id"] + " review_year does not match its date")
    report.add("Date ordering", "performance_evidence: on or after hire, year matches date",
               len(tables["performance_evidence"]), problems)

    # Effective-dated bands: the band on a salary record must cover its date.
    expired = labelled_ids(ground_truth, "EXPIRED_BAND")
    band_by_id = lookups.index_by(tables["compensation_band"], "band_id")
    problems = []
    found_expired = set()
    for record in tables["salary_record"]:
        band = band_by_id[record["band_id"]]
        covered = band["effective_from"] <= record["effective_date"] <= band["effective_to"]
        same_job = (band["role_id"] == record["role_id"] and band["level_id"] == record["level_id"]
                    and band["location_id"] == record["location_id"])
        if not same_job:
            problems.append(record["salary_record_id"] + " band is for a different job")
        if not covered:
            found_expired.add(record["salary_record_id"])
    for record_id in sorted(found_expired - expired):
        problems.append(record_id + " uses an expired band but is not labelled")
    for record_id in sorted(expired - found_expired):
        problems.append(record_id + " is labelled EXPIRED_BAND but its band is valid")
    report.add("Date ordering", "salary_record: band covers the effective date (except labelled EXPIRED_BAND)",
               len(tables["salary_record"]), problems)


def check_arithmetic(tables, ground_truth, report):
    band_lookup = metrics.build_band_lookup(tables["compensation_band"])
    rate_lookup = metrics.build_rate_lookup(tables["fx_rate"])
    location_by_id = lookups.index_by(tables["location"], "location_id")
    record_by_id = lookups.index_by(tables["salary_record"], "salary_record_id")
    employee_by_id = lookups.index_by(tables["employee"], "employee_id")

    problems = []
    for band in tables["compensation_band"]:
        mid = int(band["band_mid"])
        if int(band["band_min"]) != int(round(mid * config.BAND_MIN_FACTOR)):
            problems.append(band["band_id"] + " minimum is not 80% of midpoint")
        if int(band["band_max"]) != int(round(mid * config.BAND_MAX_FACTOR)):
            problems.append(band["band_id"] + " maximum is not 120% of midpoint")
        if not int(band["band_min"]) < mid < int(band["band_max"]):
            problems.append(band["band_id"] + " min, mid, max are not in order")
        if band["currency_code"] != location_by_id[band["location_id"]]["currency_code"]:
            problems.append(band["band_id"] + " currency differs from its location")
    report.add("Arithmetic", "compensation_band: min = 80% and max = 120% of midpoint, local currency",
               len(tables["compensation_band"]), problems)

    # Recorded compa-ratio must equal the recomputed one, except on the
    # three labelled calculation anomalies.
    exempt = (labelled_ids(ground_truth, "EXPIRED_BAND") | labelled_ids(ground_truth, "FTE_IGNORED")
              | labelled_ids(ground_truth, "FX_CONVERSION_MISSING"))
    problems = []
    mismatched = set()
    for record in tables["salary_record"]:
        band = metrics.find_band_for_date(record["role_id"], record["level_id"], record["location_id"],
                                          record["effective_date"], band_lookup)
        correct = metrics.compa_ratio(record, band, rate_lookup)
        if abs(float(record["recorded_compa_ratio"]) - correct) > config.RATIO_TOLERANCE:
            mismatched.add(record["salary_record_id"])
    for record_id in sorted(mismatched - exempt):
        problems.append(record_id + " recorded ratio is wrong but the record is not labelled")
    for record_id in sorted(exempt - mismatched):
        problems.append(record_id + " is labelled but its recorded ratio is correct")
    report.add("Arithmetic", "salary_record: recorded compa-ratio reconciles (except labelled records)",
               len(tables["salary_record"]), problems)

    problems = []
    hired = {}
    promoted_at = {}
    for employee in tables["employee"]:
        hired[employee["employee_id"]] = employee["hire_date"]
    for promotion in tables["promotion"]:
        employee_id = promotion["employee_id"]
        if employee_id not in promoted_at or promotion["effective_date"] > promoted_at[employee_id]:
            promoted_at[employee_id] = promotion["effective_date"]
    for row in tables["tenure"]:
        employee_id = row["employee_id"]
        employee = employee_by_id[employee_id]
        expected_as_of = employee["termination_date"] if employee["termination_date"] != "" else config.REVIEW_DATE
        level_start = promoted_at.get(employee_id, hired[employee_id])
        if row["as_of_date"] != expected_as_of:
            problems.append(employee_id + " tenure as_of_date is wrong")
        if int(row["company_tenure_months"]) != date_utils.months_between(hired[employee_id], row["as_of_date"]):
            problems.append(employee_id + " company tenure does not match hire date")
        if int(row["level_tenure_months"]) != date_utils.months_between(level_start, row["as_of_date"]):
            problems.append(employee_id + " level tenure does not match latest promotion")
        if int(row["level_tenure_months"]) > int(row["company_tenure_months"]):
            problems.append(employee_id + " level tenure exceeds company tenure")
    report.add("Arithmetic", "tenure: months recomputed from hire date and promotions",
               len(tables["tenure"]), problems)

    level_rank = {}
    for level in tables["level"]:
        level_rank[level["level_id"]] = int(level["level_rank"])
    problems = []
    for promotion in tables["promotion"]:
        record = record_by_id[promotion["salary_record_id"]]
        if level_rank[promotion["to_level_id"]] != level_rank[promotion["from_level_id"]] + 1:
            problems.append(promotion["promotion_id"] + " does not move up exactly one level")
        if (record["change_reason"] != "PROMOTION" or record["effective_date"] != promotion["effective_date"]
                or record["employee_id"] != promotion["employee_id"]
                or record["level_id"] != promotion["to_level_id"]):
            problems.append(promotion["promotion_id"] + " does not match its salary record")
    promotion_records = 0
    for record in tables["salary_record"]:
        if record["change_reason"] == "PROMOTION":
            promotion_records = promotion_records + 1
    if promotion_records != len(tables["promotion"]):
        problems.append("PROMOTION salary records and promotion rows differ in count")
    report.add("Arithmetic", "promotion: one level up, matches exactly one PROMOTION salary record",
               len(tables["promotion"]), problems)

    members_by_group = lookups.group_rows(tables["comparable_group_member"], "group_id")
    problems = []
    for group in tables["comparable_group"]:
        actual = len(members_by_group.get(group["group_id"], []))
        if int(group["member_count"]) != actual:
            problems.append(group["group_id"] + " member_count does not equal bridge rows")
        if group["grouping_basis"] in ["ROLE_LEVEL_LOCATION", "ROLE_LEVEL", "FAMILY_LEVEL"] and actual < config.MIN_GROUP_SIZE:
            problems.append(group["group_id"] + " is smaller than the minimum group size")
        if group["grouping_basis"] in ["ROLE_LEVEL", "FAMILY_LEVEL"] and group["rationale"] == "":
            problems.append(group["group_id"] + " is widened but has no rationale")
    report.add("Arithmetic", "comparable_group: member_count equals bridge rows, size and rationale rules",
               len(tables["comparable_group"]), problems)

    # Proposals: every number is recomputed from source records.
    member_pairs = set()
    for member in tables["comparable_group_member"]:
        member_pairs.add((member["group_id"], member["employee_id"]))
    problems = []
    for proposal in tables["adjustment_proposal"]:
        proposal_id = proposal["proposal_id"]
        basis = record_by_id[proposal["basis_salary_record_id"]]
        band = metrics.find_band_for_date(basis["role_id"], basis["level_id"], basis["location_id"],
                                          basis["effective_date"], band_lookup)
        current = int(basis["annual_amount"])
        proposed = int(proposal["proposed_annual_amount"])
        if basis["employee_id"] != proposal["employee_id"]:
            problems.append(proposal_id + " basis record belongs to another employee")
        if (proposal["group_id"], proposal["employee_id"]) not in member_pairs:
            problems.append(proposal_id + " employee is not a member of the evidence group")
        if employee_by_id[proposal["employee_id"]]["employment_status"] != "ACTIVE":
            problems.append(proposal_id + " is for a terminated employee")
        if abs(float(proposal["current_compa_ratio"]) - metrics.compa_ratio(basis, band, rate_lookup)) > config.RATIO_TOLERANCE:
            problems.append(proposal_id + " current compa-ratio does not reconcile")
        if proposed <= current:
            problems.append(proposal_id + " proposed amount is not an increase")
        if abs(float(proposal["increase_pct"]) - round((proposed - current) * 100.0 / current, 2)) > 0.011:
            problems.append(proposal_id + " increase_pct does not reconcile")
        as_proposed = dict(basis)
        as_proposed["annual_amount"] = proposed
        if metrics.normalised_salary(as_proposed, band, rate_lookup) > int(band["band_max"]) + 1:
            problems.append(proposal_id + " proposed pay is above the band maximum")
        if float(proposal["target_compa_ratio"]) <= float(proposal["current_compa_ratio"]):
            problems.append(proposal_id + " target ratio is not above current ratio")
    report.add("Arithmetic", "adjustment_proposal: ratios, increase % and band cap recomputed from sources",
               len(tables["adjustment_proposal"]), problems)

    # An applied adjustment must pay exactly the proposed amount.
    problems = []
    checked = 0
    proposal_by_id = lookups.index_by(tables["adjustment_proposal"], "proposal_id")
    applied_proposals = set()
    for record in tables["salary_record"]:
        if record["change_reason"] != "ADJUSTMENT":
            continue
        checked = checked + 1
        proposal = proposal_by_id[record["proposal_id"]]
        applied_proposals.add(record["proposal_id"])
        if record["annual_amount"] != proposal["proposed_annual_amount"]:
            problems.append(record["salary_record_id"] + " amount differs from the proposal")
        if record["employee_id"] != proposal["employee_id"]:
            problems.append(record["salary_record_id"] + " employee differs from the proposal")
        if proposal["status"] != "APPLIED":
            problems.append(record["salary_record_id"] + " exists but proposal is not APPLIED")
    for proposal in tables["adjustment_proposal"]:
        if proposal["status"] == "APPLIED" and proposal["proposal_id"] not in applied_proposals:
            problems.append(proposal["proposal_id"] + " is APPLIED but has no salary record")
    report.add("Arithmetic", "salary_record: ADJUSTMENT amount equals proposal, one per APPLIED proposal",
               checked, problems)


def check_lifecycle(tables, ground_truth, report):
    events_by_proposal = lookups.group_rows(tables["proposal_event"], "proposal_id")
    proposal_by_id = lookups.index_by(tables["adjustment_proposal"], "proposal_id")

    # Which proposals are the labelled unapproved adjustments?
    record_by_id = lookups.index_by(tables["salary_record"], "salary_record_id")
    labelled_proposals = set()
    for record_id in labelled_ids(ground_truth, "UNAPPROVED_ADJUSTMENT"):
        labelled_proposals.add(record_by_id[record_id]["proposal_id"])

    problems = []
    illegal = set()
    for proposal in tables["adjustment_proposal"]:
        proposal_id = proposal["proposal_id"]
        trail = sorted(events_by_proposal.get(proposal_id, []), key=lambda event: int(event["event_seq"]))
        if len(trail) == 0:
            problems.append(proposal_id + " has no events")
            continue
        previous_status = ""
        previous_date = proposal["created_date"]
        for position in range(len(trail)):
            event = trail[position]
            if int(event["event_seq"]) != position + 1:
                problems.append(proposal_id + " event sequence has a gap")
            if event["from_status"] != previous_status:
                problems.append(proposal_id + " event does not start from the previous status")
            if event["event_date"] < previous_date:
                problems.append(proposal_id + " events go backwards in time")
            if (event["from_status"], event["to_status"]) not in ALLOWED_TRANSITIONS:
                illegal.add(proposal_id)
            previous_status = event["to_status"]
            previous_date = event["event_date"]
        if proposal["status"] != previous_status:
            problems.append(proposal_id + " status differs from its latest event")
        if trail[0]["event_date"] != proposal["created_date"]:
            problems.append(proposal_id + " first event is not on the created date")
    report.add("Lifecycle", "proposal_event: sequence, dates and status chain are consistent",
               len(tables["proposal_event"]), problems)

    problems = []
    for proposal_id in sorted(illegal - labelled_proposals):
        problems.append(proposal_id + " has an illegal transition but is not labelled")
    for proposal_id in sorted(labelled_proposals - illegal):
        problems.append(proposal_id + " is labelled but its transitions are legal")
    report.add("Lifecycle", "proposal_event: only allowed transitions (except labelled UNAPPROVED_ADJUSTMENT)",
               len(tables["proposal_event"]), problems)

    # Decision rules: rejected and approved for the documented reasons.
    latest_rating = lookups.latest_rating_by_employee(tables["performance_evidence"], config.REVIEW_DATE)
    problems = []
    for proposal in tables["adjustment_proposal"]:
        proposal_id = proposal["proposal_id"]
        if proposal_id in labelled_proposals:
            continue
        rating = lookups.rating_or_neutral(latest_rating, proposal["employee_id"])
        increase = float(proposal["increase_pct"])
        for event in events_by_proposal[proposal_id]:
            if event["to_status"] == "REJECTED" and event["from_status"] == "SUBMITTED":
                if rating > config.REJECT_RATING_AT_OR_BELOW:
                    problems.append(proposal_id + " rejected at SUBMITTED without a low rating")
            if event["to_status"] == "REJECTED" and event["from_status"] == "HR_REVIEWED":
                if increase <= config.COMMITTEE_REJECT_ABOVE_PCT:
                    problems.append(proposal_id + " rejected by committee below the limit")
            if event["to_status"] == "APPROVED":
                if increase > config.COMMITTEE_REJECT_ABOVE_PCT or rating <= config.REJECT_RATING_AT_OR_BELOW:
                    problems.append(proposal_id + " approved against the rules")
                needed = "HR_PARTNER" if increase <= config.HR_APPROVAL_LIMIT_PCT else "COMP_COMMITTEE"
                if event["actor_role"] != needed:
                    problems.append(proposal_id + " approved by the wrong role")
    report.add("Lifecycle", "adjustment_proposal: approvals and rejections follow the documented rules",
               len(tables["adjustment_proposal"]), problems)


def check_duplicates(tables, report):
    for table in schema.TABLES:
        seen = set()
        problems = []
        for row in tables[table["name"]]:
            whole_row = tuple(row[name] for name in schema.column_names(table))
            if whole_row in seen:
                problems.append("identical row appears twice")
            seen.add(whole_row)
        report.add("Duplicates", table["name"] + ": no fully identical rows", len(tables[table["name"]]), problems)

    seen = set()
    problems = []
    for row in tables["performance_evidence"]:
        if row["evidence_type"] != "ANNUAL_RATING":
            continue
        key = (row["employee_id"], row["review_year"])
        if key in seen:
            problems.append(row["employee_id"] + " has two ratings for " + row["review_year"])
        seen.add(key)
    report.add("Duplicates", "performance_evidence: one annual rating per employee per year", len(seen), problems)

    seen = set()
    problems = []
    for record in tables["salary_record"]:
        key = (record["employee_id"], record["effective_date"])
        if key in seen:
            problems.append(record["employee_id"] + " has two salary records on " + record["effective_date"])
        seen.add(key)
    report.add("Duplicates", "salary_record: one record per employee per date", len(seen), problems)

    seen = set()
    problems = []
    for proposal in tables["adjustment_proposal"]:
        if proposal["employee_id"] in seen:
            problems.append(proposal["employee_id"] + " has two proposals in one review")
        seen.add(proposal["employee_id"])
    report.add("Duplicates", "adjustment_proposal: one proposal per employee per review", len(seen), problems)


def check_ground_truth(tables, ground_truth, csv_folder, report):
    # No input table may carry a label column.
    problems = []
    checked = 0
    for table in schema.TABLES:
        for name in schema.column_names(table):
            checked = checked + 1
            for word in LABEL_WORDS:
                if word in name:
                    problems.append(table["name"] + "." + name + " looks like a label column")
    for file_name in sorted(os.listdir(csv_folder)):
        if "ground_truth" in file_name:
            problems.append(file_name + " is inside the input folder")
    report.add("Ground truth", "no label columns or label files among the inputs", checked, problems)

    ids_by_table = {}
    for table_name, key_column in [("salary_record", "salary_record_id"), ("comparable_group", "group_id"),
                                   ("role", "role_id")]:
        ids_by_table[table_name] = set(row[key_column] for row in tables[table_name])
    problems = []
    seen = set()
    for label in ground_truth:
        if label["record_id"] not in ids_by_table.get(label["table_name"], set()):
            problems.append(label["ground_truth_id"] + " points to a record that does not exist")
        if label["record_id"] in seen:
            problems.append(label["record_id"] + " carries more than one label")
        seen.add(label["record_id"])
    report.add("Ground truth", "every label points to one existing record, one label per record",
               len(ground_truth), problems)

    # Incomparable groups: labelled groups really are mixed and lack a rationale.
    problems = []
    group_by_id = lookups.index_by(tables["comparable_group"], "group_id")
    for group_id in labelled_ids(ground_truth, "INCOMPARABLE_GROUP"):
        if group_by_id[group_id]["rationale"] != "" or group_by_id[group_id]["grouping_basis"] != "CUSTOM":
            problems.append(group_id + " is labelled but has a rationale")
    for group in tables["comparable_group"]:
        if group["grouping_basis"] == "CUSTOM" and group["rationale"] == "":
            if group["group_id"] not in labelled_ids(ground_truth, "INCOMPARABLE_GROUP"):
                problems.append(group["group_id"] + " has no rationale but is not labelled")
    report.add("Ground truth", "INCOMPARABLE_GROUP labels match groups with no rationale",
               len(tables["comparable_group"]), problems)


def check_coverage(tables, ground_truth, expected_employees, report):
    problems = []
    combos = set()
    for band in tables["compensation_band"]:
        combos.add((band["role_id"], band["level_id"]))
    if len(combos) != 200:
        problems.append("expected 200 role/level combinations in bands, found " + str(len(combos)))
    used = set()
    for record in tables["salary_record"]:
        used.add((record["role_id"], record["level_id"]))
    if len(used) != 200:
        problems.append("expected all 200 role/level combinations in use, found " + str(len(used)))
    if len(tables["employee"]) != expected_employees:
        problems.append("expected " + str(expected_employees) + " employees, found " + str(len(tables["employee"])))
    years = set()
    for record in tables["salary_record"]:
        years.add(record["effective_date"][0:4])
    if years != set(["2024", "2025", "2026"]):
        problems.append("salary history does not cover 2024-2026")
    report.add("Coverage", "200 role/level combinations, employee count, three years of history", 4, problems)

    problems = []
    reasons = set(record["change_reason"] for record in tables["salary_record"])
    for reason in ["PROMOTION", "FTE_CHANGE", "RELOCATION", "ADJUSTMENT"]:
        if reason not in reasons:
            problems.append("no " + reason + " records")
    band_by_id = lookups.index_by(tables["compensation_band"], "band_id")
    cross_currency = 0
    for record in tables["salary_record"]:
        if record["currency_code"] != band_by_id[record["band_id"]]["currency_code"]:
            cross_currency = cross_currency + 1
    if cross_currency == 0:
        problems.append("no salary paid in a different currency from its band")
    statuses = set(proposal["status"] for proposal in tables["adjustment_proposal"])
    for status in ["DRAFT", "SUBMITTED", "HR_REVIEWED", "REJECTED", "APPLIED"]:
        if status not in statuses:
            problems.append("no proposal in status " + status)
    labelled = set(label["issue_type"] for label in ground_truth)
    for issue_type in ["EXPIRED_BAND", "FTE_IGNORED", "FX_CONVERSION_MISSING", "UNAPPROVED_ADJUSTMENT",
                       "INCOMPARABLE_GROUP", "UNEXPLAINED_OUTLIER_LOW", "UNEXPLAINED_OUTLIER_HIGH"]:
        if issue_type not in labelled:
            problems.append("no labelled case of " + issue_type)
    expected_systemic = int(round(config.INJECT_SYSTEMIC_ROLES[0] * expected_employees / 5000.0))
    if expected_systemic > 0 and "SYSTEMIC_DISPARITY" not in labelled:
        problems.append("no labelled case of SYSTEMIC_DISPARITY")
    report.add("Coverage", "promotions, part-time, currency changes, all statuses and all edge cases present",
               len(tables["salary_record"]), problems)

    problems = []
    with_group = set(row["employee_id"] for row in tables["demographics"])
    for employee in tables["employee"]:
        if employee["employee_id"] not in with_group:
            problems.append(employee["employee_id"] + " has no demographics row")
    groups_seen = set(row["demographic_group"] for row in tables["demographics"])
    if len(groups_seen) < 2:
        problems.append("only one demographic group is present")
    report.add("Coverage", "demographics: one row for every employee, both groups present",
               len(tables["employee"]), problems)


def check_sql_seed(tables, sql_folder, report):
    """Load schema.sql and seed.sql into an in-memory database."""
    problems = []
    connection = sqlite3.connect(":memory:")
    try:
        with open(os.path.join(sql_folder, "schema.sql"), "r", encoding="utf-8") as f:
            connection.executescript(f.read())
        with open(os.path.join(sql_folder, "seed.sql"), "r", encoding="utf-8") as f:
            connection.executescript(f.read())
        for table in schema.TABLES:
            count = connection.execute('SELECT COUNT(*) FROM "' + table["name"] + '"').fetchone()[0]
            if count != len(tables[table["name"]]):
                problems.append(table["name"] + " has " + str(count) + " rows in SQL, CSV has "
                                + str(len(tables[table["name"]])))
        broken = connection.execute("PRAGMA foreign_key_check").fetchall()
        if len(broken) > 0:
            problems.append(str(len(broken)) + " foreign key violations inside the database")
    except sqlite3.Error as error:
        problems.append("SQL failed to load: " + str(error))
    connection.close()
    report.add("Exports", "SQL seed loads into SQLite, row counts match CSV, database FK check is clean",
               len(schema.TABLES), problems)


def check_json(tables, json_folder, report):
    import json
    problems = []
    for table in schema.TABLES:
        with open(os.path.join(json_folder, table["name"] + ".json"), "r", encoding="utf-8") as f:
            rows = json.load(f)
        if len(rows) != len(tables[table["name"]]):
            problems.append(table["name"] + " JSON row count differs from CSV")
    report.add("Exports", "JSON files parse and row counts match CSV", len(schema.TABLES), problems)


def run_validation(data_folder, truth_folder, expected_employees):
    csv_folder = os.path.join(data_folder, "csv")
    tables = io_utils.read_all_tables(csv_folder)
    ground_truth = io_utils.read_csv(os.path.join(truth_folder, "ground_truth.csv"))

    report = Report()
    check_primary_keys(tables, report)
    check_foreign_keys(tables, report)
    check_enums(tables, report)
    check_id_formats(tables, report)
    if not report.all_passed():
        # The remaining checks join tables together. With broken keys those
        # joins cannot be trusted, so stop here and report it clearly.
        report.add("Skipped", "date, arithmetic, lifecycle and other join-based checks", 0,
                   ["not run because a key, enum or ID check failed first"])
        return report
    check_dates(tables, ground_truth, report)
    check_arithmetic(tables, ground_truth, report)
    check_lifecycle(tables, ground_truth, report)
    check_duplicates(tables, report)
    check_ground_truth(tables, ground_truth, csv_folder, report)
    check_coverage(tables, ground_truth, expected_employees, report)
    check_sql_seed(tables, os.path.join(data_folder, "sql"), report)
    check_json(tables, os.path.join(data_folder, "json"), report)
    return report


REPORT_COLUMNS = ["category", "check", "status", "records_checked", "problems", "first_problem"]


def main():
    parser = argparse.ArgumentParser(description="Validate a generated dataset.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--data", default="data")
    parser.add_argument("--truth", default="ground_truth")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    report = run_validation(os.path.join(args.data, args.scale), os.path.join(args.truth, args.scale),
                            config.SCALES[args.scale])
    out_folder = os.path.join(args.out, args.scale)
    io_utils.write_csv(report.rows, out_folder, "validation_summary.csv", REPORT_COLUMNS)

    passed = 0
    by_category = {}
    for row in report.rows:
        entry = by_category.setdefault(row["category"], [0, 0])
        entry[1] = entry[1] + 1
        if row["status"] == "PASS":
            passed = passed + 1
            entry[0] = entry[0] + 1

    text = "# Validation summary (" + args.scale + ")\n\n"
    text = text + str(passed) + " of " + str(len(report.rows)) + " checks passed.\n\n"
    text = text + "| Category | Passed | Total |\n|---|---|---|\n"
    for category in by_category:
        text = text + "| " + category + " | " + str(by_category[category][0]) + " | " + str(by_category[category][1]) + " |\n"
    text = text + "\n| Category | Check | Status | Records checked | Problems |\n|---|---|---|---|---|\n"
    for row in report.rows:
        text = text + ("| " + row["category"] + " | " + row["check"] + " | " + row["status"] + " | "
                       + str(row["records_checked"]) + " | " + str(row["problems"]) + " |\n")
    io_utils.write_text(os.path.join(out_folder, "validation_summary.md"), text)

    print("Validation (" + args.scale + "):", passed, "of", len(report.rows), "checks passed")
    for category in by_category:
        print("  " + category.ljust(16) + str(by_category[category][0]).rjust(3) + " / " + str(by_category[category][1]))
    for row in report.rows:
        if row["status"] != "PASS":
            print("  FAIL:", row["check"], "-", row["problems"], "problems, e.g.", row["first_problem"])
    print("Written to", out_folder)
    if not report.all_passed():
        sys.exit(1)


if __name__ == "__main__":
    main()
