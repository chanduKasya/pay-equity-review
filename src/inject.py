"""
inject.py - adds the deliberate, labelled edge cases AFTER the valid
baseline data exists, and builds the ground truth table.

Rules followed here:
  - Only the record that carries the anomaly is changed.
  - A record or employee gets at most one injected issue.
  - The label is written ONLY to the ground truth rows returned by this
    module. No input table gets an issue column.
"""

import config
import date_utils
import lookups
import metrics
import rand_utils
import review

DECISION = {
    "EXPIRED_BAND": "RECALCULATE",
    "FTE_IGNORED": "RECALCULATE",
    "FX_CONVERSION_MISSING": "RECALCULATE",
    "UNAPPROVED_ADJUSTMENT": "REVERSE_OR_RATIFY",
    "INCOMPARABLE_GROUP": "REGROUP",
    "UNEXPLAINED_OUTLIER_LOW": "PROPOSE_INCREASE",
    "UNEXPLAINED_OUTLIER_HIGH": "FLAG_FOR_REVIEW",
    "SYSTEMIC_DISPARITY": "GROUP_PAY_REVIEW",
}


def add_label(ground_truth, issue_type, table_name, record_id, employee_id, detail):
    ground_truth.append({
        "ground_truth_id": "GT-" + str(len(ground_truth) + 1).zfill(6),
        "issue_type": issue_type,
        "table_name": table_name,
        "record_id": record_id,
        "employee_id": employee_id,
        "expected_decision": DECISION[issue_type],
        "detail": detail,
    })


def inject_all(rng, employee_count, salary_records, outlier_info, snapshot, roles,
               groups, members, proposals, events, waiting_at_hr,
               band_lookup, rate_lookup, salary_counters, affected_roles):
    ground_truth = []
    used_employees = set()

    # ---- 0. Unexplained outliers (pay was multiplied in history.py) ----
    latest = lookups.latest_salary_by_employee(salary_records, config.REVIEW_DATE)
    for employee_id in sorted(outlier_info.keys()):
        direction = outlier_info[employee_id]
        add_label(ground_truth, "UNEXPLAINED_OUTLIER_" + direction, "salary_record",
                  latest[employee_id]["salary_record_id"], employee_id,
                  "Pay set " + direction.lower() + " against the documented policy with no evidence record")
        used_employees.add(employee_id)

    # Proposal-linked records are left alone so the approval trail stays clean.
    for proposal in proposals:
        used_employees.add(proposal["employee_id"])

    band_by_id = {}
    for key in band_lookup:
        for band in band_lookup[key]:
            band_by_id[band["band_id"]] = band

    # ---- 1. Salary compared to an expired band ----
    candidates = []
    for record in salary_records:
        if record["employee_id"] in used_employees:
            continue
        if date_utils.year_of(record["effective_date"]) >= 2025:
            candidates.append(record)
    wanted = rand_utils.scaled_count(config.INJECT_EXPIRED_BAND, employee_count)
    for record in choose(rng, candidates, wanted, used_employees):
        year = date_utils.year_of(record["effective_date"])
        old_date = str(year - 1) + "-06-30"
        old_band = metrics.find_band_for_date(record["role_id"], record["level_id"],
                                              record["location_id"], old_date, band_lookup)
        record["band_id"] = old_band["band_id"]
        record["recorded_compa_ratio"] = format(metrics.compa_ratio(record, old_band, rate_lookup), ".4f")
        add_label(ground_truth, "EXPIRED_BAND", "salary_record", record["salary_record_id"],
                  record["employee_id"],
                  "Compared against " + old_band["band_id"] + " which expired on " + old_band["effective_to"])

    # ---- 2. FTE ignored ----
    candidates = []
    for record in salary_records:
        if record["employee_id"] not in used_employees and float(record["fte"]) < 1.0:
            candidates.append(record)
    wanted = rand_utils.scaled_count(config.INJECT_FTE_IGNORED, employee_count)
    for record in choose(rng, candidates, wanted, used_employees):
        band = band_by_id[record["band_id"]]
        as_if_full_time = dict(record)
        as_if_full_time["fte"] = "1.00"
        record["recorded_compa_ratio"] = format(metrics.compa_ratio(as_if_full_time, band, rate_lookup), ".4f")
        add_label(ground_truth, "FTE_IGNORED", "salary_record", record["salary_record_id"],
                  record["employee_id"],
                  "Part-time pay at FTE " + record["fte"] + " compared to the full-time band without dividing by FTE")

    # ---- 3. Currency conversion missing ----
    candidates = []
    for record in salary_records:
        band = band_by_id[record["band_id"]]
        if record["employee_id"] not in used_employees and record["currency_code"] != band["currency_code"]:
            candidates.append(record)
    wanted = rand_utils.scaled_count(config.INJECT_FX_MISSING, employee_count)
    for record in choose(rng, candidates, wanted, used_employees):
        band = band_by_id[record["band_id"]]
        raw_ratio = float(record["annual_amount"]) / float(record["fte"]) / float(band["band_mid"])
        record["recorded_compa_ratio"] = format(round(raw_ratio, 4), ".4f")
        add_label(ground_truth, "FX_CONVERSION_MISSING", "salary_record", record["salary_record_id"],
                  record["employee_id"],
                  "Salary in " + record["currency_code"] + " divided by a " + band["currency_code"]
                  + " band midpoint without conversion")

    # ---- 4. Adjustment applied without approval ----
    wanted = rand_utils.scaled_count(config.INJECT_UNAPPROVED, employee_count)
    chosen = rand_utils.shuffled(rng, waiting_at_hr)[0:wanted]
    chosen.sort(key=lambda proposal: proposal["proposal_id"])
    events_by_proposal = lookups.group_rows(events, "proposal_id")
    record_by_id = lookups.index_by(salary_records, "salary_record_id")
    new_records = []
    for proposal in chosen:
        last_event = events_by_proposal[proposal["proposal_id"]][-1]
        sequence = int(last_event["event_seq"]) + 1
        applied_date = date_utils.add_days(last_event["event_date"], 4)
        number = proposal["proposal_id"][len("ADJ-2026-"):]
        events.append({
            "event_id": "ADJEVT-2026-" + number + "-" + str(sequence).zfill(2),
            "proposal_id": proposal["proposal_id"],
            "event_seq": sequence,
            "event_date": applied_date,
            "from_status": "HR_REVIEWED",
            "to_status": "APPLIED",        # the APPROVED step was skipped
            "actor_role": "SYSTEM",
        })
        proposal["status"] = "APPLIED"
        basis = record_by_id[proposal["basis_salary_record_id"]]
        new_record = review.make_adjustment_record(basis, proposal, applied_date,
                                                   band_lookup, rate_lookup, salary_counters)
        new_records.append(new_record)
        add_label(ground_truth, "UNAPPROVED_ADJUSTMENT", "salary_record",
                  new_record["salary_record_id"], proposal["employee_id"],
                  "Proposal " + proposal["proposal_id"] + " was applied with no APPROVED event")
    events.sort(key=lambda event: event["event_id"])

    # ---- 5. Incomparable roles grouped without rationale ----
    ids_by_family = {}
    for person in snapshot:
        ids_by_family.setdefault(person["job_family"], []).append(person["employee_id"])
    families = sorted(ids_by_family.keys())
    wanted = rand_utils.scaled_count(config.INJECT_BAD_GROUPS, employee_count)
    for _ in range(wanted):
        two_families = rand_utils.shuffled(rng, families)[0:2]
        chosen_ids = []
        for family in two_families:
            size = rand_utils.rand_int(rng, 3, 5)
            chosen_ids = chosen_ids + rand_utils.shuffled(rng, ids_by_family[family])[0:size]
        group_id = "GRP-2026-" + str(len(groups) + 1).zfill(6)
        groups.append({
            "group_id": group_id,
            "grouping_basis": "CUSTOM",
            "role_id": "",
            "level_id": "",
            "location_id": "",
            "job_family": "",
            "rationale": "",               # the missing rationale is the anomaly
            "member_count": len(chosen_ids),
        })
        for employee_id in sorted(chosen_ids):
            members.append({"group_id": group_id, "employee_id": employee_id})
        add_label(ground_truth, "INCOMPARABLE_GROUP", "comparable_group", group_id, "",
                  "Employees from " + two_families[0] + " and " + two_families[1]
                  + " grouped together with no rationale")

    # ---- 6. Systemic disparity (pay was reduced in history.py) ----
    reduction = int(round((1 - config.SYSTEMIC_PAY_MULTIPLIER) * 100))
    for role_id in affected_roles:
        add_label(ground_truth, "SYSTEMIC_DISPARITY", "role", role_id, "",
                  config.DISADVANTAGED_GROUP + " pay set " + str(reduction)
                  + "% lower than the policy at every level of this role")

    return ground_truth, new_records


def choose(rng, candidates, wanted, used_employees):
    """Pick up to `wanted` records, one per employee, and mark them used."""
    chosen = []
    for record in rand_utils.shuffled(rng, candidates):
        if len(chosen) >= wanted:
            break
        if record["employee_id"] in used_employees:
            continue
        used_employees.add(record["employee_id"])
        chosen.append(record)
    return chosen
