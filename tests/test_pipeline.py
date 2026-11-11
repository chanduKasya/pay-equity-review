"""End-to-end tests on a freshly generated 500-employee dataset."""

import os
import shutil

import pytest

import config
import detect
import evaluate
import generate
import io_utils
import schema
import validate

SEED = config.DEFAULT_SEED
COUNT = 500


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    """Generate once and share the folders between the tests."""
    root = tmp_path_factory.mktemp("dataset")
    data_folder = os.path.join(str(root), "data")
    truth_folder = os.path.join(str(root), "ground_truth")
    tables, ground_truth = generate.build_dataset(SEED, COUNT)
    generate.write_dataset(tables, ground_truth, SEED, "starter", data_folder, truth_folder)
    return {"data": data_folder, "truth": truth_folder, "tables": tables, "ground_truth": ground_truth}


def copy_dataset(dataset, tmp_path):
    """A private copy, so a test can damage it without affecting others."""
    data_copy = os.path.join(str(tmp_path), "data")
    shutil.copytree(dataset["data"], data_copy)
    return data_copy


def rewrite_table(data_folder, table_name, rows):
    table = schema.get_table(table_name)
    io_utils.write_csv(rows, os.path.join(data_folder, "csv"), table_name + ".csv", schema.column_names(table))


def failed_checks(report):
    return [row["check"] for row in report.rows if row["status"] != "PASS"]


# ---------------- reproducibility ----------------

def test_same_seed_gives_identical_data(dataset):
    tables_again, truth_again = generate.build_dataset(SEED, COUNT)
    assert tables_again == dataset["tables"]
    assert truth_again == dataset["ground_truth"]


def test_different_seed_gives_different_data(dataset):
    tables_other, _ = generate.build_dataset(SEED + 1, COUNT)
    assert tables_other["salary_record"] != dataset["tables"]["salary_record"]
    assert tables_other["role"] == dataset["tables"]["role"]      # master data is fixed


# ---------------- volume and coverage ----------------

def test_volume_and_role_level_coverage(dataset):
    tables = dataset["tables"]
    assert len(tables["employee"]) == COUNT
    combos = set((band["role_id"], band["level_id"]) for band in tables["compensation_band"])
    assert len(combos) == 200
    assert len(tables["compensation_band"]) == 200 * 8 * 3


def test_all_seven_issue_types_are_labelled(dataset):
    labelled = set(label["issue_type"] for label in dataset["ground_truth"])
    assert labelled == {"EXPIRED_BAND", "FTE_IGNORED", "FX_CONVERSION_MISSING", "UNAPPROVED_ADJUSTMENT",
                        "INCOMPARABLE_GROUP", "UNEXPLAINED_OUTLIER_LOW", "UNEXPLAINED_OUTLIER_HIGH"}


def test_no_label_leaks_into_input_tables(dataset):
    for table in schema.TABLES:
        for name in schema.column_names(table):
            assert "issue" not in name and "truth" not in name and "anomaly" not in name
    assert "ground_truth.csv" not in os.listdir(os.path.join(dataset["data"], "csv"))


# ---------------- validation ----------------

def test_clean_dataset_passes_every_check(dataset):
    report = validate.run_validation(dataset["data"], dataset["truth"], COUNT)
    assert failed_checks(report) == []


def test_validator_catches_a_broken_foreign_key(dataset, tmp_path):
    data_copy = copy_dataset(dataset, tmp_path)
    rows = io_utils.read_csv(os.path.join(data_copy, "csv", "salary_record.csv"))
    rows[10]["employee_id"] = "EMP-999999"
    rewrite_table(data_copy, "salary_record", rows)
    report = validate.run_validation(data_copy, dataset["truth"], COUNT)
    assert "salary_record.employee_id -> employee.employee_id" in failed_checks(report)


def test_validator_catches_a_duplicate_key(dataset, tmp_path):
    data_copy = copy_dataset(dataset, tmp_path)
    rows = io_utils.read_csv(os.path.join(data_copy, "csv", "employee.csv"))
    rows.append(dict(rows[0]))
    rewrite_table(data_copy, "employee", rows)
    report = validate.run_validation(data_copy, dataset["truth"], COUNT)
    assert "employee: key is unique and not empty" in failed_checks(report)


def test_validator_catches_an_unlabelled_wrong_ratio(dataset, tmp_path):
    data_copy = copy_dataset(dataset, tmp_path)
    labelled = set(label["record_id"] for label in dataset["ground_truth"])
    rows = io_utils.read_csv(os.path.join(data_copy, "csv", "salary_record.csv"))
    for row in rows:
        if row["salary_record_id"] not in labelled:
            row["recorded_compa_ratio"] = "9.9999"
            break
    rewrite_table(data_copy, "salary_record", rows)
    report = validate.run_validation(data_copy, dataset["truth"], COUNT)
    assert "salary_record: recorded compa-ratio reconciles (except labelled records)" in failed_checks(report)


def test_validator_catches_an_illegal_status_jump(dataset, tmp_path):
    data_copy = copy_dataset(dataset, tmp_path)
    rows = io_utils.read_csv(os.path.join(data_copy, "csv", "proposal_event.csv"))
    for row in rows:
        if row["to_status"] == "SUBMITTED":
            row["to_status"] = "APPROVED"      # DRAFT -> APPROVED is not allowed
            break
    rewrite_table(data_copy, "proposal_event", rows)
    report = validate.run_validation(data_copy, dataset["truth"], COUNT)
    assert len(failed_checks(report)) > 0


# ---------------- detection and evaluation ----------------

def test_detector_works_without_the_ground_truth_folder(dataset, tmp_path):
    # Only the input tables are copied. No ground truth exists in tmp_path.
    data_copy = copy_dataset(dataset, tmp_path)
    findings, metric_rows, policy, _ = detect.run_detection(os.path.join(data_copy, "csv"))
    assert len(findings) > 0
    assert len(metric_rows) > 0


def test_detector_finds_every_rule_based_edge_case(dataset):
    findings, metric_rows, policy, _ = detect.run_detection(os.path.join(dataset["data"], "csv"))
    rows, misses, matched, correct_decisions, sweep = evaluate.run_evaluation(
        findings, dataset["ground_truth"], metric_rows)
    by_type = {row["issue_type"]: row for row in rows}
    for issue_type in ["EXPIRED_BAND", "FTE_IGNORED", "FX_CONVERSION_MISSING",
                       "UNAPPROVED_ADJUSTMENT", "INCOMPARABLE_GROUP"]:
        assert by_type[issue_type]["recall"] == "1.000", issue_type
        assert by_type[issue_type]["precision"] == "1.000", issue_type
    assert float(by_type["ALL"]["recall"]) >= 0.90
    assert float(by_type["ALL"]["precision"]) >= 0.90
    assert correct_decisions == matched


def test_valid_custom_group_with_rationale_is_not_flagged(dataset):
    findings, _, _, _ = detect.run_detection(os.path.join(dataset["data"], "csv"))
    flagged = set(f["record_id"] for f in findings if f["issue_type"] == "INCOMPARABLE_GROUP")
    documented = [group["group_id"] for group in dataset["tables"]["comparable_group"]
                  if group["grouping_basis"] == "CUSTOM" and group["rationale"] != ""]
    assert len(documented) >= 1
    for group_id in documented:
        assert group_id not in flagged


def test_history_is_append_only(dataset):
    # An applied proposal adds a record; the basis record still exists unchanged.
    records = {r["salary_record_id"]: r for r in dataset["tables"]["salary_record"]}
    applied = [p for p in dataset["tables"]["adjustment_proposal"] if p["status"] == "APPLIED"]
    assert len(applied) > 0
    for proposal in applied:
        basis = records[proposal["basis_salary_record_id"]]
        assert basis["change_reason"] != "ADJUSTMENT"
        assert int(basis["annual_amount"]) < int(proposal["proposed_annual_amount"])


def test_detector_estimates_the_policy_from_data(dataset):
    # The detector is never given these numbers; it has to recover them.
    # 500 employees is a small sample, so the tolerances are loose.
    _, _, policy, _ = detect.run_detection(os.path.join(dataset["data"], "csv"))
    assert abs(policy["base_ratio"] - config.POLICY_BASE_RATIO) < 0.03
    assert abs(policy["per_rating_point"] - config.POLICY_PER_RATING_POINT) < 0.006
    assert abs(policy["per_premium_unit"] - 1.0) < 0.1
    # Total effect of reaching the tenure cap: 5 years x 0.02 = 0.10.
    full_tenure_effect = policy["per_tenure_year"] * policy["tenure_cap_years"]
    true_effect = config.POLICY_PER_TENURE_YEAR * config.POLICY_TENURE_CAP_YEARS
    assert abs(full_tenure_effect - true_effect) < 0.03


def test_detect_module_does_not_use_the_generator_policy():
    source = open(os.path.join(os.path.dirname(detect.__file__), "detect.py"), encoding="utf-8").read()
    assert "POLICY_" not in source
    assert "expected_compa_ratio(" not in source


# ---------------- systemic disparity (needs the full 5,000 employees) ----------------

@pytest.fixture(scope="module")
def full_dataset(tmp_path_factory):
    root = tmp_path_factory.mktemp("full")
    data_folder = os.path.join(str(root), "data")
    truth_folder = os.path.join(str(root), "ground_truth")
    tables, ground_truth = generate.build_dataset(SEED, 5000)
    generate.write_dataset(tables, ground_truth, SEED, "full", data_folder, truth_folder)
    return {"data": data_folder, "tables": tables, "ground_truth": ground_truth}


def test_every_employee_has_one_demographic_group(dataset):
    rows = dataset["tables"]["demographics"]
    assert len(rows) == COUNT
    assert set(row["demographic_group"] for row in rows) == set(config.DEMOGRAPHIC_GROUPS)


def test_small_dataset_has_no_systemic_label_and_no_systemic_flag(dataset):
    # 500 employees leave too few people per role and level to compare groups.
    labelled = [l for l in dataset["ground_truth"] if l["issue_type"] == "SYSTEMIC_DISPARITY"]
    findings, _, _, _ = detect.run_detection(os.path.join(dataset["data"], "csv"))
    flagged = [f for f in findings if f["issue_type"] == "SYSTEMIC_DISPARITY"]
    assert labelled == []
    assert flagged == []


def test_systemic_disparity_is_found_in_exactly_the_affected_roles(full_dataset):
    labelled = set(l["record_id"] for l in full_dataset["ground_truth"] if l["issue_type"] == "SYSTEMIC_DISPARITY")
    findings, _, _, _ = detect.run_detection(os.path.join(full_dataset["data"], "csv"))
    flagged = set(f["record_id"] for f in findings if f["issue_type"] == "SYSTEMIC_DISPARITY")
    assert len(labelled) == config.INJECT_SYSTEMIC_ROLES[0]
    assert flagged == labelled


def test_people_in_a_systemic_finding_are_not_also_individual_outliers(full_dataset):
    findings, metric_rows, _, _ = detect.run_detection(os.path.join(full_dataset["data"], "csv"))
    covered = [row for row in metric_rows if row["in_systemic_finding"] == "YES"]
    assert len(covered) > 0
    for row in covered:
        assert row["outlier_flag"] != "UNEXPLAINED_OUTLIER_LOW"
