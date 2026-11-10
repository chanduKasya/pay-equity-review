"""
lookups.py - helpers that answer "what is the latest X for each employee?"
Used by the review workflow, the detector and the validator.
"""

import config


def index_by(rows, key_field):
    """Turn a list of rows into a dictionary: key value -> row."""
    result = {}
    for row in rows:
        result[row[key_field]] = row
    return result


def group_rows(rows, key_field):
    """key value -> list of rows that share it (original order kept)."""
    result = {}
    for row in rows:
        key = row[key_field]
        if key not in result:
            result[key] = []
        result[key].append(row)
    return result


def latest_salary_by_employee(salary_records, as_of_date):
    """Each employee's most recent salary record on or before as_of_date."""
    latest = {}
    for record in salary_records:
        if record["effective_date"] > as_of_date:
            continue
        employee_id = record["employee_id"]
        if employee_id not in latest or record["effective_date"] > latest[employee_id]["effective_date"]:
            latest[employee_id] = record
    return latest


def latest_rating_by_employee(evidence, as_of_date):
    """Most recent annual rating. Employees with no rating are left out."""
    latest_date = {}
    latest_rating = {}
    for row in evidence:
        if row["evidence_type"] != "ANNUAL_RATING":
            continue
        if row["evidence_date"] > as_of_date:
            continue
        employee_id = row["employee_id"]
        if employee_id not in latest_date or row["evidence_date"] > latest_date[employee_id]:
            latest_date[employee_id] = row["evidence_date"]
            latest_rating[employee_id] = int(row["rating"])
    return latest_rating


def premium_by_employee(evidence, as_of_date):
    """Documented critical-skill premium (percent). Missing means 0."""
    premium = {}
    for row in evidence:
        if row["evidence_type"] != "CRITICAL_SKILL_PREMIUM":
            continue
        if row["evidence_date"] > as_of_date:
            continue
        premium[row["employee_id"]] = float(row["premium_pct"])
    return premium


def rating_or_neutral(latest_rating, employee_id):
    """New hires have no rating yet, so the neutral rating is used."""
    if employee_id in latest_rating:
        return latest_rating[employee_id]
    return config.POLICY_NEUTRAL_RATING
