"""
schema.py - one description of every table.

The CSV writer, the JSON and SQL exports and the validator all read this
file, so column names and keys are defined in exactly one place.

Each table has:
  name    : table name (also the file name)
  columns : list of (column name, type). Types: TEXT, INTEGER, REAL
  pk      : list of primary key columns
  fks     : list of (column, parent table, parent column)
"""

TABLES = [
    {
        "name": "role",
        "columns": [("role_id", "TEXT"), ("role_name", "TEXT"), ("job_family", "TEXT"),
                    ("base_mid_usd", "INTEGER")],
        "pk": ["role_id"],
        "fks": [],
    },
    {
        "name": "level",
        "columns": [("level_id", "TEXT"), ("level_name", "TEXT"), ("level_rank", "INTEGER"),
                    ("mid_multiplier", "REAL")],
        "pk": ["level_id"],
        "fks": [],
    },
    {
        "name": "location",
        "columns": [("location_id", "TEXT"), ("city", "TEXT"), ("country", "TEXT"),
                    ("currency_code", "TEXT"), ("geo_factor", "REAL")],
        "pk": ["location_id"],
        "fks": [],
    },
    {
        "name": "fx_rate",
        "columns": [("currency_code", "TEXT"), ("rate_year", "INTEGER"), ("units_per_usd", "REAL")],
        "pk": ["currency_code", "rate_year"],
        "fks": [],
    },
    {
        "name": "compensation_band",
        "columns": [("band_id", "TEXT"), ("role_id", "TEXT"), ("level_id", "TEXT"),
                    ("location_id", "TEXT"), ("band_year", "INTEGER"), ("currency_code", "TEXT"),
                    ("band_min", "INTEGER"), ("band_mid", "INTEGER"), ("band_max", "INTEGER"),
                    ("effective_from", "TEXT"), ("effective_to", "TEXT")],
        "pk": ["band_id"],
        "fks": [("role_id", "role", "role_id"), ("level_id", "level", "level_id"),
                ("location_id", "location", "location_id")],
    },
    {
        "name": "employee",
        "columns": [("employee_id", "TEXT"), ("hire_date", "TEXT"), ("employment_status", "TEXT"),
                    ("termination_date", "TEXT"), ("manager_employee_id", "TEXT")],
        "pk": ["employee_id"],
        "fks": [("manager_employee_id", "employee", "employee_id")],
    },
    {
        "name": "demographics",
        "columns": [("employee_id", "TEXT"), ("demographic_group", "TEXT")],
        "pk": ["employee_id"],
        "fks": [("employee_id", "employee", "employee_id")],
    },
    {
        "name": "salary_record",
        "columns": [("salary_record_id", "TEXT"), ("employee_id", "TEXT"), ("effective_date", "TEXT"),
                    ("role_id", "TEXT"), ("level_id", "TEXT"), ("location_id", "TEXT"),
                    ("band_id", "TEXT"), ("currency_code", "TEXT"), ("fte", "REAL"),
                    ("annual_amount", "INTEGER"), ("change_reason", "TEXT"), ("proposal_id", "TEXT"),
                    ("recorded_compa_ratio", "REAL")],
        "pk": ["salary_record_id"],
        "fks": [("employee_id", "employee", "employee_id"), ("role_id", "role", "role_id"),
                ("level_id", "level", "level_id"), ("location_id", "location", "location_id"),
                ("band_id", "compensation_band", "band_id"),
                ("proposal_id", "adjustment_proposal", "proposal_id")],
    },
    {
        "name": "performance_evidence",
        "columns": [("evidence_id", "TEXT"), ("employee_id", "TEXT"), ("evidence_type", "TEXT"),
                    ("evidence_date", "TEXT"), ("review_year", "INTEGER"), ("rating", "INTEGER"),
                    ("premium_pct", "REAL")],
        "pk": ["evidence_id"],
        "fks": [("employee_id", "employee", "employee_id")],
    },
    {
        "name": "promotion",
        "columns": [("promotion_id", "TEXT"), ("employee_id", "TEXT"), ("effective_date", "TEXT"),
                    ("from_level_id", "TEXT"), ("to_level_id", "TEXT"), ("salary_record_id", "TEXT")],
        "pk": ["promotion_id"],
        "fks": [("employee_id", "employee", "employee_id"), ("from_level_id", "level", "level_id"),
                ("to_level_id", "level", "level_id"),
                ("salary_record_id", "salary_record", "salary_record_id")],
    },
    {
        "name": "tenure",
        "columns": [("employee_id", "TEXT"), ("as_of_date", "TEXT"),
                    ("company_tenure_months", "INTEGER"), ("level_tenure_months", "INTEGER")],
        "pk": ["employee_id"],
        "fks": [("employee_id", "employee", "employee_id")],
    },
    {
        "name": "comparable_group",
        "columns": [("group_id", "TEXT"), ("grouping_basis", "TEXT"), ("role_id", "TEXT"),
                    ("level_id", "TEXT"), ("location_id", "TEXT"), ("job_family", "TEXT"),
                    ("rationale", "TEXT"), ("member_count", "INTEGER")],
        "pk": ["group_id"],
        "fks": [("role_id", "role", "role_id"), ("level_id", "level", "level_id"),
                ("location_id", "location", "location_id")],
    },
    {
        "name": "comparable_group_member",
        "columns": [("group_id", "TEXT"), ("employee_id", "TEXT")],
        "pk": ["group_id", "employee_id"],
        "fks": [("group_id", "comparable_group", "group_id"),
                ("employee_id", "employee", "employee_id")],
    },
    {
        "name": "adjustment_proposal",
        "columns": [("proposal_id", "TEXT"), ("employee_id", "TEXT"), ("group_id", "TEXT"),
                    ("basis_salary_record_id", "TEXT"), ("created_date", "TEXT"),
                    ("current_compa_ratio", "REAL"), ("group_median_compa_ratio", "REAL"),
                    ("target_compa_ratio", "REAL"), ("proposed_annual_amount", "INTEGER"),
                    ("increase_pct", "REAL"), ("evidence_summary", "TEXT"), ("status", "TEXT")],
        "pk": ["proposal_id"],
        "fks": [("employee_id", "employee", "employee_id"),
                ("group_id", "comparable_group", "group_id"),
                ("basis_salary_record_id", "salary_record", "salary_record_id")],
    },
    {
        "name": "proposal_event",
        "columns": [("event_id", "TEXT"), ("proposal_id", "TEXT"), ("event_seq", "INTEGER"),
                    ("event_date", "TEXT"), ("from_status", "TEXT"), ("to_status", "TEXT"),
                    ("actor_role", "TEXT")],
        "pk": ["event_id"],
        "fks": [("proposal_id", "adjustment_proposal", "proposal_id")],
    },
]

# The labels table is kept apart from the input tables on purpose.
GROUND_TRUTH = {
    "name": "ground_truth",
    "columns": [("ground_truth_id", "TEXT"), ("issue_type", "TEXT"), ("table_name", "TEXT"),
                ("record_id", "TEXT"), ("employee_id", "TEXT"), ("expected_decision", "TEXT"),
                ("detail", "TEXT")],
    "pk": ["ground_truth_id"],
    "fks": [],
}


def column_names(table):
    names = []
    for column in table["columns"]:
        names.append(column[0])
    return names


def get_table(name):
    for table in TABLES:
        if table["name"] == name:
            return table
    return None
