"""
history.py - builds three years of salary history for every employee.

Output tables: SalaryRecord, Promotion, PerformanceEvidence.

How one employee's history is built:
  1. Work out the list of dated events (ratings, annual reviews, promotion
     checks, a possible FTE change, a possible relocation).
  2. Sort the events by date.
  3. Walk through them in order. Every pay change ADDS a salary record.
     No record is ever edited afterwards (append-only history).

Pay is always set from the documented policy in metrics.expected_compa_ratio,
plus a small personal variation. A few employees are deliberately made
"unexplained outliers" by multiplying their pay. They are returned in
outlier_info so that the label can be written to the ground truth file.
"""

import config
import date_utils
import metrics
import rand_utils


def next_salary_id(employee_id, effective_date, counters):
    """SAL-<employee-id>-<year>-<seq>. seq counts records in that year."""
    year = effective_date[0:4]
    key = (employee_id, year)
    counters[key] = counters.get(key, 0) + 1
    return "SAL-" + employee_id + "-" + year + "-" + str(counters[key]).zfill(2)


def make_salary_record(state, effective_date, change_reason, proposal_id,
                       band_lookup, rate_lookup, counters):
    """Create one salary record from the employee's current state."""
    band = metrics.find_band_for_date(state["role_id"], state["level_id"],
                                      state["location_id"], effective_date, band_lookup)
    year = date_utils.year_of(effective_date)

    # full_time_salary is held in the band's currency. Apply FTE first,
    # then convert if the employee is paid in a different currency.
    amount = state["full_time_salary"] * state["fte"]
    amount = metrics.convert_currency(amount, band["currency_code"],
                                      state["pay_currency"], year, rate_lookup)
    record = {
        "salary_record_id": next_salary_id(state["employee_id"], effective_date, counters),
        "employee_id": state["employee_id"],
        "effective_date": effective_date,
        "role_id": state["role_id"],
        "level_id": state["level_id"],
        "location_id": state["location_id"],
        "band_id": band["band_id"],
        "currency_code": state["pay_currency"],
        "fte": format(state["fte"], ".2f"),
        "annual_amount": int(round(amount)),
        "change_reason": change_reason,
        "proposal_id": proposal_id,
        "recorded_compa_ratio": "",
    }
    # The recorded ratio is derived from the stored values, never invented.
    ratio = metrics.compa_ratio(record, band, rate_lookup)
    record["recorded_compa_ratio"] = format(ratio, ".4f")
    return record


def policy_salary(state, effective_date, band_lookup):
    """Full-time salary the pay policy gives this employee on this date."""
    band = metrics.find_band_for_date(state["role_id"], state["level_id"],
                                      state["location_id"], effective_date, band_lookup)
    tenure_months = date_utils.months_between(state["level_start"], effective_date)
    expected = metrics.expected_compa_ratio(tenure_months, state["rating"], state["premium_pct"])
    ratio = expected + state["noise"]
    if ratio < config.POLICY_RATIO_FLOOR:
        ratio = config.POLICY_RATIO_FLOOR
    ratio = ratio * state["outlier_multiplier"]
    return metrics.round_to_100(float(band["band_mid"]) * ratio)


def build_history(rng, employees, start_jobs, levels, locations, band_lookup, rate_lookup):
    level_rank = {}
    level_by_rank = {}
    for level in levels:
        level_rank[level["level_id"]] = int(level["level_rank"])
        level_by_rank[int(level["level_rank"])] = level["level_id"]

    location_currency = {}
    location_ids = []
    for location in locations:
        location_currency[location["location_id"]] = location["currency_code"]
        location_ids.append(location["location_id"])

    salary_records = []
    promotions = []
    evidence = []
    outlier_info = {}
    final_states = {}
    salary_counters = {}

    for employee in employees:
        employee_id = employee["employee_id"]
        job = start_jobs[employee_id]

        start_date = employee["hire_date"]
        if start_date < config.HISTORY_START:
            start_date = config.HISTORY_START
        end_date = employee["termination_date"]
        if end_date == "":
            end_date = config.HISTORY_END

        # ---- draw this employee's random traits (always in the same order) ----
        noise = rand_utils.rand_float(rng, -config.NORMAL_NOISE, config.NORMAL_NOISE)
        skill_roll = rng.random()
        premium_value = rand_utils.rand_int(rng, 5, 20)
        outlier_roll = rng.random()
        outlier_low = rand_utils.rand_float(rng, config.OUTLIER_LOW_RANGE[0], config.OUTLIER_LOW_RANGE[1])
        outlier_high = rand_utils.rand_float(rng, config.OUTLIER_HIGH_RANGE[0], config.OUTLIER_HIGH_RANGE[1])
        fte_roll = rng.random()
        fte_year = rand_utils.pick(rng, config.BAND_YEARS)
        fte_month = rand_utils.pick(rng, ["02", "09"])
        fte_value = rand_utils.pick(rng, config.PART_TIME_FTES)
        fte_return_roll = rng.random()
        move_roll = rng.random()
        move_year = rand_utils.pick(rng, config.BAND_YEARS)
        move_location = rand_utils.pick(rng, location_ids)
        keep_currency_roll = rng.random()

        premium_pct = 0
        if skill_roll < config.SHARE_CRITICAL_SKILL:
            premium_pct = premium_value

        # Deliberate unexplained outliers: active employees with no premium.
        outlier_multiplier = 1.0
        if employee["employment_status"] == "ACTIVE" and premium_pct == 0:
            if outlier_roll < config.SHARE_OUTLIER_LOW:
                outlier_multiplier = outlier_low
                outlier_info[employee_id] = "LOW"
            elif outlier_roll < config.SHARE_OUTLIER_LOW + config.SHARE_OUTLIER_HIGH:
                outlier_multiplier = outlier_high
                outlier_info[employee_id] = "HIGH"

        state = {
            "employee_id": employee_id,
            "role_id": job["role_id"],
            "level_id": job["level_id"],
            "location_id": job["location_id"],
            "fte": 1.0,
            "pay_currency": location_currency[job["location_id"]],
            "level_start": employee["hire_date"],
            "rating": config.POLICY_NEUTRAL_RATING,
            "premium_pct": premium_pct,
            "noise": noise,
            "outlier_multiplier": outlier_multiplier,
            "full_time_salary": 0,
        }

        # ---- first record ----
        if employee["hire_date"] >= config.HISTORY_START:
            first_reason = "HIRE"
        else:
            first_reason = "OPENING_BALANCE"
        state["full_time_salary"] = policy_salary(state, start_date, band_lookup)
        salary_records.append(make_salary_record(state, start_date, first_reason, "",
                                                 band_lookup, rate_lookup, salary_counters))

        evidence_counters = {}
        if premium_pct > 0:
            evidence.append(make_evidence(employee_id, "CRITICAL_SKILL_PREMIUM", start_date,
                                          "", premium_pct, evidence_counters))

        # ---- list the dated events ----
        events = []
        for year in config.BAND_YEARS:
            year_text = str(year)
            if employee["hire_date"] < year_text + "-01-01":
                events.append((year_text + "-03-15", "RATING"))
                events.append((year_text + "-04-01", "ANNUAL_REVIEW"))
            events.append((year_text + "-07-01", "PROMOTION_CHECK"))
        if fte_roll < config.SHARE_PART_TIME_CHANGE:
            fte_date = str(fte_year) + "-" + fte_month + "-01"
            events.append((fte_date, "GO_PART_TIME"))
            if fte_return_roll < config.SHARE_RETURN_TO_FULL_TIME:
                back_date = str(fte_year + 1) + "-" + fte_month + "-01"
                events.append((back_date, "GO_FULL_TIME"))
        if move_roll < config.SHARE_RELOCATION and move_location != job["location_id"]:
            events.append((str(move_year) + "-10-01", "RELOCATION"))
        events.sort()

        promotion_count = 0

        # ---- walk through the events in date order ----
        for event_date, event_type in events:
            if event_date <= start_date or event_date > end_date:
                continue

            if event_type == "RATING":
                state["rating"] = rand_utils.pick_weighted(rng, config.RATING_WEIGHTS)
                evidence.append(make_evidence(employee_id, "ANNUAL_RATING", event_date,
                                              state["rating"], "", evidence_counters))

            elif event_type == "ANNUAL_REVIEW":
                new_salary = policy_salary(state, event_date, band_lookup)
                # Pay is never cut at an annual review.
                if new_salary < state["full_time_salary"]:
                    new_salary = state["full_time_salary"]
                state["full_time_salary"] = new_salary
                # After a relocation, pay moves to the local currency here.
                state["pay_currency"] = location_currency[state["location_id"]]
                salary_records.append(make_salary_record(state, event_date, "ANNUAL_REVIEW", "",
                                                         band_lookup, rate_lookup, salary_counters))

            elif event_type == "PROMOTION_CHECK":
                promote_roll = rng.random()
                rank = level_rank[state["level_id"]]
                months_in_level = date_utils.months_between(state["level_start"], event_date)
                eligible = rank < 5 and state["rating"] >= 4 and months_in_level >= 12
                if eligible and promote_roll < config.PROMOTION_CHANCE:
                    old_level = state["level_id"]
                    old_salary = state["full_time_salary"]
                    state["level_id"] = level_by_rank[rank + 1]
                    state["level_start"] = event_date
                    new_salary = policy_salary(state, event_date, band_lookup)
                    # A promotion always comes with at least a 3% raise.
                    minimum_salary = metrics.round_to_100(old_salary * 1.03)
                    if new_salary < minimum_salary:
                        new_salary = minimum_salary
                    state["full_time_salary"] = new_salary
                    record = make_salary_record(state, event_date, "PROMOTION", "",
                                                band_lookup, rate_lookup, salary_counters)
                    salary_records.append(record)
                    promotion_count = promotion_count + 1
                    promotions.append({
                        "promotion_id": "PROMO-" + employee_id + "-" + str(promotion_count).zfill(2),
                        "employee_id": employee_id,
                        "effective_date": event_date,
                        "from_level_id": old_level,
                        "to_level_id": state["level_id"],
                        "salary_record_id": record["salary_record_id"],
                    })

            elif event_type == "GO_PART_TIME" or event_type == "GO_FULL_TIME":
                # Only the hours change. The full-time salary stays the same.
                if event_type == "GO_PART_TIME":
                    state["fte"] = fte_value
                else:
                    state["fte"] = 1.0
                salary_records.append(make_salary_record(state, event_date, "FTE_CHANGE", "",
                                                         band_lookup, rate_lookup, salary_counters))

            elif event_type == "RELOCATION":
                # Keep the same compa-ratio against the new location's band.
                old_band = metrics.find_band_for_date(state["role_id"], state["level_id"],
                                                      state["location_id"], event_date, band_lookup)
                current_ratio = state["full_time_salary"] / float(old_band["band_mid"])
                old_currency = state["pay_currency"]
                state["location_id"] = move_location
                new_band = metrics.find_band_for_date(state["role_id"], state["level_id"],
                                                      state["location_id"], event_date, band_lookup)
                state["full_time_salary"] = metrics.round_to_100(float(new_band["band_mid"]) * current_ratio)
                new_currency = location_currency[move_location]
                if new_currency != old_currency and keep_currency_roll < config.SHARE_KEEP_OLD_CURRENCY:
                    state["pay_currency"] = old_currency   # paid in the old currency for now
                else:
                    state["pay_currency"] = new_currency
                salary_records.append(make_salary_record(state, event_date, "RELOCATION", "",
                                                         band_lookup, rate_lookup, salary_counters))

        final_states[employee_id] = state

    return salary_records, promotions, evidence, outlier_info, final_states, salary_counters


def make_evidence(employee_id, evidence_type, evidence_date, rating, premium_pct, counters):
    year = evidence_date[0:4]
    counters[year] = counters.get(year, 0) + 1
    return {
        "evidence_id": "PERF-" + employee_id + "-" + year + "-" + str(counters[year]).zfill(2),
        "employee_id": employee_id,
        "evidence_type": evidence_type,
        "evidence_date": evidence_date,
        "review_year": int(year),
        "rating": rating,
        "premium_pct": premium_pct,
    }


def build_tenure(employees, promotions):
    """Tenure is derived from hire date and promotions, never generated."""
    latest_promotion = {}
    for promotion in promotions:
        employee_id = promotion["employee_id"]
        if employee_id not in latest_promotion or promotion["effective_date"] > latest_promotion[employee_id]:
            latest_promotion[employee_id] = promotion["effective_date"]

    tenure_rows = []
    for employee in employees:
        employee_id = employee["employee_id"]
        as_of_date = config.REVIEW_DATE
        if employee["termination_date"] != "":
            as_of_date = employee["termination_date"]
        level_start = employee["hire_date"]
        if employee_id in latest_promotion:
            level_start = latest_promotion[employee_id]
        tenure_rows.append({
            "employee_id": employee_id,
            "as_of_date": as_of_date,
            "company_tenure_months": date_utils.months_between(employee["hire_date"], as_of_date),
            "level_tenure_months": date_utils.months_between(level_start, as_of_date),
        })
    return tenure_rows
