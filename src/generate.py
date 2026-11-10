"""
generate.py - builds the whole synthetic dataset with one command.

Run from the project folder:
    python3 src/generate.py --scale starter
    python3 src/generate.py --scale full --seed 20261022

Output:
    data/<scale>/csv/*.csv          one file per table
    data/<scale>/json/*.json        the same tables as JSON
    data/<scale>/sql/schema.sql     CREATE TABLE statements
    data/<scale>/sql/seed.sql       INSERT statements
    data/<scale>/manifest.json      seed, row counts and checksums
    ground_truth/<scale>/           the labels, kept apart from the inputs
"""

import argparse
import json
import os

import config
import employees as employees_module
import history
import inject
import io_utils
import master_data
import metrics
import rand_utils
import review
import schema


def build_dataset(seed, employee_count):
    """Run every stage in dependency order. Returns (tables, ground_truth)."""
    # ---- Stage 1: master tables (parents first, no randomness) ----
    roles = master_data.build_roles()
    levels = master_data.build_levels()
    locations = master_data.build_locations()
    fx_rates = master_data.build_fx_rates()
    bands = master_data.build_bands(roles, levels, locations, fx_rates)
    band_lookup = metrics.build_band_lookup(bands)
    rate_lookup = metrics.build_rate_lookup(fx_rates)

    # ---- Stage 2: employees ----
    rng = rand_utils.make_rng(seed, 2)
    employees, start_jobs = employees_module.build_employees(rng, employee_count, roles, levels, locations)

    # ---- Stage 3: salary history, promotions, performance evidence ----
    rng = rand_utils.make_rng(seed, 3)
    result = history.build_history(rng, employees, start_jobs, levels, locations, band_lookup, rate_lookup)
    salary_records, promotions, evidence, outlier_info, final_states, salary_counters = result

    # ---- Stage 4: derived tenure ----
    tenure_rows = history.build_tenure(employees, promotions)

    # ---- Stage 5: review workflow (groups, proposals, approval trail) ----
    rng = rand_utils.make_rng(seed, 5)
    snapshot = review.build_review_snapshot(employees, salary_records, evidence, tenure_rows,
                                            roles, band_lookup, rate_lookup)
    groups, members, primary_group = review.build_groups(rng, snapshot, employee_count)
    proposals, events, applied_records, waiting_at_hr = review.run_proposals(
        rng, snapshot, groups, members, primary_group, band_lookup, rate_lookup, salary_counters)

    # ---- Stage 6: labelled edge cases, injected after the valid baseline ----
    rng = rand_utils.make_rng(seed, 6)
    ground_truth, unapproved_records = inject.inject_all(
        rng, employee_count, salary_records, outlier_info, snapshot, roles,
        groups, members, proposals, events, waiting_at_hr,
        band_lookup, rate_lookup, salary_counters)

    # New salary records are appended. Existing ones were never removed.
    salary_records = salary_records + applied_records + unapproved_records
    salary_records.sort(key=lambda record: record["salary_record_id"])

    tables = {
        "role": roles,
        "level": levels,
        "location": locations,
        "fx_rate": fx_rates,
        "compensation_band": bands,
        "employee": employees,
        "salary_record": salary_records,
        "performance_evidence": evidence,
        "promotion": promotions,
        "tenure": tenure_rows,
        "comparable_group": groups,
        "comparable_group_member": members,
        "adjustment_proposal": proposals,
        "proposal_event": events,
    }
    return tables, ground_truth


def write_dataset(tables, ground_truth, seed, scale, data_folder, truth_folder):
    """Write CSV, JSON and SQL, then a manifest with checksums."""
    csv_folder = os.path.join(data_folder, "csv")
    json_folder = os.path.join(data_folder, "json")
    sql_folder = os.path.join(data_folder, "sql")

    written = []
    row_counts = {}
    for table in schema.TABLES:
        rows = tables[table["name"]]
        row_counts[table["name"]] = len(rows)
        written.append(io_utils.write_csv(rows, csv_folder, table["name"] + ".csv",
                                          schema.column_names(table)))
        written.append(io_utils.write_json(rows, table, json_folder))
    written.append(io_utils.write_sql_schema(sql_folder))
    written.append(io_utils.write_sql_seed(tables, sql_folder))

    truth_table = schema.GROUND_TRUTH
    truth_files = []
    truth_files.append(io_utils.write_csv(ground_truth, truth_folder, "ground_truth.csv",
                                          schema.column_names(truth_table)))
    truth_files.append(io_utils.write_json(ground_truth, truth_table, truth_folder))

    manifest = {
        "generator": "src/generate.py",
        "command": "python3 src/generate.py --scale " + scale + " --seed " + str(seed),
        "seed": seed,
        "scale": scale,
        "employee_count": row_counts["employee"],
        "history_window": [config.HISTORY_START, config.HISTORY_END],
        "review_date": config.REVIEW_DATE,
        "external_data_sources": [],
        "provenance": "Fully synthetic. No external or personal data was used.",
        "row_counts": row_counts,
        "ground_truth_rows": len(ground_truth),
        "files": {},
    }
    for path in written:
        relative = os.path.relpath(path, data_folder).replace(os.sep, "/")
        manifest["files"][relative] = io_utils.sha256_of_file(path)
    for path in truth_files:
        manifest["files"]["ground_truth/" + os.path.basename(path)] = io_utils.sha256_of_file(path)

    io_utils.write_text(os.path.join(data_folder, "manifest.json"),
                        json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate the synthetic pay-equity dataset.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    parser.add_argument("--out", default="data", help="folder for the input tables")
    parser.add_argument("--truth", default="ground_truth", help="folder for the labels")
    args = parser.parse_args()

    employee_count = config.SCALES[args.scale]
    data_folder = os.path.join(args.out, args.scale)
    truth_folder = os.path.join(args.truth, args.scale)

    print("Generating: scale =", args.scale, "| employees =", employee_count, "| seed =", args.seed)
    tables, ground_truth = build_dataset(args.seed, employee_count)
    manifest = write_dataset(tables, ground_truth, args.seed, args.scale, data_folder, truth_folder)

    for name in manifest["row_counts"]:
        print("  " + name.ljust(26) + str(manifest["row_counts"][name]).rjust(8))
    print("  " + "ground_truth".ljust(26) + str(len(ground_truth)).rjust(8))
    print("Written to", data_folder, "and", truth_folder)


if __name__ == "__main__":
    main()
