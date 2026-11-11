"""
employees.py - builds the Employee table.

It also returns each employee's starting job (role, level, location).
That starting job is not a column of the Employee table, because jobs change
over time. It is recorded on the employee's first salary record instead.
"""

import config
import date_utils
import rand_utils


def build_employees(rng, employee_count, roles, levels, locations):
    # Every role x level pair, so the first 200 employees cover all 200 pairs.
    combos = []
    for role in roles:
        for level in levels:
            combos.append((role["role_id"], level["level_id"]))

    role_ids = []
    for role in roles:
        role_ids.append(role["role_id"])

    days_before_window = date_utils.days_between("2016-01-01", "2023-12-31")
    days_in_window = date_utils.days_between(config.HISTORY_START, "2026-09-30")

    employees = []
    start_jobs = {}

    for number in range(1, employee_count + 1):
        employee_id = "EMP-" + str(number).zfill(6)

        if number <= len(combos):
            role_id = combos[number - 1][0]
            level_id = combos[number - 1][1]
        else:
            role_id = rand_utils.pick(rng, role_ids)
            level_id = rand_utils.pick_weighted(rng, config.LEVEL_WEIGHTS)
        location_id = rand_utils.pick_weighted(rng, config.LOCATION_WEIGHTS)

        # Hire date: most people joined before the history window starts.
        if rng.random() < config.SHARE_HIRED_BEFORE_WINDOW:
            hire_date = date_utils.add_days("2016-01-01", rand_utils.rand_int(rng, 0, days_before_window))
        else:
            hire_date = date_utils.add_days(config.HISTORY_START, rand_utils.rand_int(rng, 0, days_in_window))

        # Some employees have left. They must have worked at least 60 days
        # inside the history window before leaving.
        employment_status = "ACTIVE"
        termination_date = ""
        leaves = rng.random() < config.SHARE_TERMINATED
        leave_roll = rng.random()
        if leaves:
            first_day = hire_date
            if first_day < config.HISTORY_START:
                first_day = config.HISTORY_START
            earliest = date_utils.add_days(first_day, 60)
            if earliest < config.HISTORY_END:
                span = date_utils.days_between(earliest, config.HISTORY_END)
                termination_date = date_utils.add_days(earliest, int(leave_roll * (span + 1)))
                employment_status = "TERMINATED"

        employees.append({
            "employee_id": employee_id,
            "hire_date": hire_date,
            "employment_status": employment_status,
            "termination_date": termination_date,
            "manager_employee_id": "",
        })
        start_jobs[employee_id] = {
            "role_id": role_id,
            "level_id": level_id,
            "location_id": location_id,
        }

    assign_managers(rng, employees, start_jobs)
    return employees, start_jobs


def build_demographics(rng, employees, start_jobs, roles, employee_count):
    """Give every employee an anonymous group label, then choose the roles
    in which one group is deliberately underpaid (the systemic disparity).

    Returns:
      demographics    : the table rows
      affected_roles  : sorted list of role IDs with the injected pay gap
      underpaid       : set of employee IDs whose pay is reduced
    """
    demographics = []
    group_of = {}
    for employee in employees:
        if rng.random() < config.SHARE_GROUP_B:
            group = "Group B"
        else:
            group = "Group A"
        group_of[employee["employee_id"]] = group
        demographics.append({"employee_id": employee["employee_id"], "demographic_group": group})

    role_ids = []
    for role in roles:
        role_ids.append(role["role_id"])
    wanted = rand_utils.scaled_count(config.INJECT_SYSTEMIC_ROLES, employee_count)
    affected_roles = sorted(rand_utils.shuffled(rng, role_ids)[0:wanted])

    underpaid = set()
    for employee in employees:
        employee_id = employee["employee_id"]
        in_affected_role = start_jobs[employee_id]["role_id"] in affected_roles
        if in_affected_role and group_of[employee_id] == config.DISADVANTAGED_GROUP:
            underpaid.add(employee_id)
    return demographics, affected_roles, underpaid


def assign_managers(rng, employees, start_jobs):
    """L1-L3 report to an L4 or L5. L4 reports to an L5. L5 has no manager."""
    senior_pool = []
    top_pool = []
    for employee in employees:
        level_id = start_jobs[employee["employee_id"]]["level_id"]
        if level_id == "L4" or level_id == "L5":
            senior_pool.append(employee["employee_id"])
        if level_id == "L5":
            top_pool.append(employee["employee_id"])

    for employee in employees:
        level_id = start_jobs[employee["employee_id"]]["level_id"]
        if level_id == "L5":
            continue
        if level_id == "L4":
            pool = top_pool
        else:
            pool = senior_pool
        if len(pool) == 0:
            continue
        manager_id = rand_utils.pick(rng, pool)
        if manager_id != employee["employee_id"]:
            employee["manager_employee_id"] = manager_id
