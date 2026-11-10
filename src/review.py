"""
review.py - the pay review workflow on the snapshot date.

Steps:
  1. Take each active employee's latest salary record and compute the
     correct compa-ratio (FTE and currency normalised, effective-dated band).
  2. Put employees into comparable groups, widening groups that are too small.
  3. Create an adjustment proposal when pay is clearly below what the
     documented factors predict.
  4. Move each proposal through its approval steps. Every step is saved as
     an event, and the decisions follow fixed rules.
  5. An APPLIED proposal adds a new salary record (history is never edited).
"""

import config
import date_utils
import history
import lookups
import metrics
import rand_utils

WIDENED_TEXT = "SMALL_GROUP_WIDENED: fewer than 5 active employees share this role, level and location"
FAMILY_TEXT = "SMALL_GROUP_WIDENED_TO_FAMILY: fewer than 5 active employees share this role and level"
VALID_CUSTOM_TEXT = "CROSS_FUNCTIONAL_COHORT: mixed group approved by HR for a documented project-pay study"


def build_review_snapshot(employees, salary_records, evidence, tenure_rows, roles,
                          band_lookup, rate_lookup):
    """One dictionary per active employee with everything the review needs."""
    family_of_role = {}
    for role in roles:
        family_of_role[role["role_id"]] = role["job_family"]

    latest_salary = lookups.latest_salary_by_employee(salary_records, config.REVIEW_DATE)
    latest_rating = lookups.latest_rating_by_employee(evidence, config.REVIEW_DATE)
    premium = lookups.premium_by_employee(evidence, config.REVIEW_DATE)
    tenure = lookups.index_by(tenure_rows, "employee_id")

    snapshot = []
    for employee in employees:
        if employee["employment_status"] != "ACTIVE":
            continue
        employee_id = employee["employee_id"]
        record = latest_salary[employee_id]
        band = metrics.find_band_for_date(record["role_id"], record["level_id"],
                                          record["location_id"], record["effective_date"], band_lookup)
        rating = lookups.rating_or_neutral(latest_rating, employee_id)
        premium_pct = premium.get(employee_id, 0.0)
        level_tenure = int(tenure[employee_id]["level_tenure_months"])
        snapshot.append({
            "employee_id": employee_id,
            "record": record,
            "band": band,
            "role_id": record["role_id"],
            "level_id": record["level_id"],
            "location_id": record["location_id"],
            "job_family": family_of_role[record["role_id"]],
            "compa_ratio": metrics.compa_ratio(record, band, rate_lookup),
            "rating": rating,
            "premium_pct": premium_pct,
            "level_tenure_months": level_tenure,
            "expected_ratio": metrics.expected_compa_ratio(level_tenure, rating, premium_pct),
        })
    return snapshot


def build_groups(rng, snapshot, employee_count):
    """Return groups, bridge rows and each employee's primary group."""
    # Count employees at each of the three widths.
    by_cell = {}
    by_role_level = {}
    by_family_level = {}
    for person in snapshot:
        cell = (person["role_id"], person["level_id"], person["location_id"])
        role_level = (person["role_id"], person["level_id"])
        family_level = (person["job_family"], person["level_id"])
        by_cell.setdefault(cell, []).append(person["employee_id"])
        by_role_level.setdefault(role_level, []).append(person["employee_id"])
        by_family_level.setdefault(family_level, []).append(person["employee_id"])

    # Decide which groups are needed. Start narrow, widen only when too small.
    needed_cells = set()
    needed_role_levels = set()
    needed_family_levels = set()
    primary_key = {}
    for person in snapshot:
        cell = (person["role_id"], person["level_id"], person["location_id"])
        role_level = (person["role_id"], person["level_id"])
        family_level = (person["job_family"], person["level_id"])
        if len(by_cell[cell]) >= config.MIN_GROUP_SIZE:
            needed_cells.add(cell)
            primary_key[person["employee_id"]] = ("ROLE_LEVEL_LOCATION", cell)
        elif len(by_role_level[role_level]) >= config.MIN_GROUP_SIZE:
            needed_role_levels.add(role_level)
            primary_key[person["employee_id"]] = ("ROLE_LEVEL", role_level)
        elif len(by_family_level[family_level]) >= config.MIN_GROUP_SIZE:
            needed_family_levels.add(family_level)
            primary_key[person["employee_id"]] = ("FAMILY_LEVEL", family_level)
        # Otherwise the employee has no comparable group and is not reviewed.

    groups = []
    members = []
    group_id_of_key = {}

    def add_group(basis, role_id, level_id, location_id, job_family, rationale, member_ids):
        group_id = "GRP-2026-" + str(len(groups) + 1).zfill(6)
        groups.append({
            "group_id": group_id,
            "grouping_basis": basis,
            "role_id": role_id,
            "level_id": level_id,
            "location_id": location_id,
            "job_family": job_family,
            "rationale": rationale,
            "member_count": len(member_ids),
        })
        for employee_id in sorted(member_ids):
            members.append({"group_id": group_id, "employee_id": employee_id})
        return group_id

    for cell in sorted(needed_cells):
        group_id = add_group("ROLE_LEVEL_LOCATION", cell[0], cell[1], cell[2], "", "", by_cell[cell])
        group_id_of_key[("ROLE_LEVEL_LOCATION", cell)] = group_id
    for key in sorted(needed_role_levels):
        group_id = add_group("ROLE_LEVEL", key[0], key[1], "", "", WIDENED_TEXT, by_role_level[key])
        group_id_of_key[("ROLE_LEVEL", key)] = group_id
    for key in sorted(needed_family_levels):
        group_id = add_group("FAMILY_LEVEL", "", key[1], "", key[0], FAMILY_TEXT, by_family_level[key])
        group_id_of_key[("FAMILY_LEVEL", key)] = group_id

    # A few valid custom groups: mixed jobs, but WITH a documented rationale.
    all_ids = []
    for person in snapshot:
        all_ids.append(person["employee_id"])
    valid_custom = rand_utils.scaled_count(config.VALID_CUSTOM_GROUPS, employee_count)
    for _ in range(valid_custom):
        size = rand_utils.rand_int(rng, 6, 10)
        chosen = rand_utils.shuffled(rng, all_ids)[0:size]
        add_group("CUSTOM", "", "", "", "", VALID_CUSTOM_TEXT, chosen)

    primary_group = {}
    for employee_id in primary_key:
        primary_group[employee_id] = group_id_of_key[primary_key[employee_id]]
    return groups, members, primary_group


def run_proposals(rng, snapshot, groups, members, primary_group,
                  band_lookup, rate_lookup, salary_counters):
    """Create proposals, their approval events and resulting salary records."""
    ratio_of = {}
    for person in snapshot:
        ratio_of[person["employee_id"]] = person["compa_ratio"]

    group_median = {}
    group_size = {}
    for group_id, rows in lookups.group_rows(members, "group_id").items():
        values = []
        for row in rows:
            values.append(ratio_of[row["employee_id"]])
        group_median[group_id] = round(metrics.median(values), 4)
        group_size[group_id] = len(values)

    proposals = []
    events = []
    new_salary_records = []
    waiting_at_hr = []      # proposals paused at HR_REVIEWED (used by the injector)

    for person in snapshot:
        employee_id = person["employee_id"]
        if employee_id not in primary_group:
            continue
        gap = person["expected_ratio"] - person["compa_ratio"]
        if gap <= config.PROPOSAL_GAP_THRESHOLD:
            continue

        record = person["record"]
        band = person["band"]
        fte = float(record["fte"])
        year = date_utils.year_of(config.REVIEW_DATE)

        # Target: the expected ratio, but never above the band maximum.
        target_full_time = metrics.round_to_100(float(band["band_mid"]) * person["expected_ratio"])
        if target_full_time > int(band["band_max"]):
            target_full_time = int(band["band_max"])
        target_ratio = round(target_full_time / float(band["band_mid"]), 4)
        proposed = metrics.convert_currency(target_full_time * fte, band["currency_code"],
                                            record["currency_code"], year, rate_lookup)
        proposed_amount = int(round(proposed))
        current_amount = int(record["annual_amount"])
        if proposed_amount <= current_amount or target_ratio <= person["compa_ratio"]:
            continue
        increase_pct = round((proposed_amount - current_amount) * 100.0 / current_amount, 2)

        number = str(len(proposals) + 1).zfill(6)
        proposal_id = "ADJ-2026-" + number
        group_id = primary_group[employee_id]
        created_date = date_utils.add_days(config.REVIEW_DATE, rand_utils.rand_int(rng, 0, 3))

        # How far has this proposal got by the end of the data? Most are
        # finished; some are still in progress. A fixed repeating pattern
        # (instead of a random roll) guarantees every stage appears even in
        # the small starter dataset. Slots: 0 = still a draft,
        # 1 = submitted, 2 and 3 = waiting after HR review, 4-11 = finished.
        slot = len(proposals) % 12

        evidence_summary = (
            "compa-ratio " + format(person["compa_ratio"], ".4f")
            + " vs expected " + format(person["expected_ratio"], ".4f")
            + " (level tenure " + str(person["level_tenure_months"]) + " months, rating "
            + str(person["rating"]) + ", premium " + format(person["premium_pct"], ".0f") + "%); "
            + "group median " + format(group_median[group_id], ".4f")
            + " over " + str(group_size[group_id]) + " employees"
        )

        # ---- approval trail: each step is one event ----
        trail = [("", "DRAFT", "MANAGER", 0)]
        if slot != 0:
            trail.append(("DRAFT", "SUBMITTED", "MANAGER", 2))
            if person["rating"] <= config.REJECT_RATING_AT_OR_BELOW:
                # Exception path: no off-cycle raise for a low rating.
                trail.append(("SUBMITTED", "REJECTED", "HR_PARTNER", 4))
            elif slot != 1:
                trail.append(("SUBMITTED", "HR_REVIEWED", "HR_PARTNER", 7))
                if slot >= 4:
                    if increase_pct > config.COMMITTEE_REJECT_ABOVE_PCT:
                        # Exception path: too large for a single cycle.
                        trail.append(("HR_REVIEWED", "REJECTED", "COMP_COMMITTEE", 11))
                    else:
                        if increase_pct <= config.HR_APPROVAL_LIMIT_PCT:
                            approver = "HR_PARTNER"
                        else:
                            approver = "COMP_COMMITTEE"
                        trail.append(("HR_REVIEWED", "APPROVED", approver, 11))
                        trail.append(("APPROVED", "APPLIED", "SYSTEM", 14))

        sequence = 0
        for from_status, to_status, actor_role, day_offset in trail:
            sequence = sequence + 1
            events.append({
                "event_id": "ADJEVT-2026-" + number + "-" + str(sequence).zfill(2),
                "proposal_id": proposal_id,
                "event_seq": sequence,
                "event_date": date_utils.add_days(created_date, day_offset),
                "from_status": from_status,
                "to_status": to_status,
                "actor_role": actor_role,
            })
        final_status = trail[-1][1]

        proposal = {
            "proposal_id": proposal_id,
            "employee_id": employee_id,
            "group_id": group_id,
            "basis_salary_record_id": record["salary_record_id"],
            "created_date": created_date,
            "current_compa_ratio": format(person["compa_ratio"], ".4f"),
            "group_median_compa_ratio": format(group_median[group_id], ".4f"),
            "target_compa_ratio": format(target_ratio, ".4f"),
            "proposed_annual_amount": proposed_amount,
            "increase_pct": format(increase_pct, ".2f"),
            "evidence_summary": evidence_summary,
            "status": final_status,
        }
        proposals.append(proposal)

        if final_status == "APPLIED":
            applied_date = date_utils.add_days(created_date, 14)
            new_salary_records.append(make_adjustment_record(
                record, proposal, applied_date, band_lookup, rate_lookup, salary_counters))
        if final_status == "HR_REVIEWED":
            waiting_at_hr.append(proposal)

    return proposals, events, new_salary_records, waiting_at_hr


def make_adjustment_record(basis_record, proposal, applied_date, band_lookup, rate_lookup, salary_counters):
    """The new salary record created when a proposal is applied."""
    band = metrics.find_band_for_date(basis_record["role_id"], basis_record["level_id"],
                                      basis_record["location_id"], applied_date, band_lookup)
    record = dict(basis_record)   # copy, so the old record is left untouched
    record["salary_record_id"] = history.next_salary_id(basis_record["employee_id"], applied_date, salary_counters)
    record["effective_date"] = applied_date
    record["band_id"] = band["band_id"]
    record["annual_amount"] = proposal["proposed_annual_amount"]
    record["change_reason"] = "ADJUSTMENT"
    record["proposal_id"] = proposal["proposal_id"]
    record["recorded_compa_ratio"] = format(metrics.compa_ratio(record, band, rate_lookup), ".4f")
    return record
