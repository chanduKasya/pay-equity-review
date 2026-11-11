"""
app.py - an interactive dashboard over the project's files.

It only READS what the pipeline already produced (data/, output/,
ground_truth/). It does not change any data. The pay formulas are imported
from src/metrics.py, so the app and the pipeline share one definition.

Run from the project folder:
    streamlit run app.py
"""

import os
import subprocess
import sys

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_FOLDER, "src"))

import config      # noqa: E402  (imported after the path is set)
import metrics     # noqa: E402
import schema      # noqa: E402

# Colours: one blue for ordinary marks, orange for the second series,
# grey for context. Status colours are used only for pass / fail states.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#c3c2b7"
INK_MUTED = "#898781"
GRID = "#e1e0d9"

ISSUE_NAMES = {
    "EXPIRED_BAND": "Expired band",
    "FTE_IGNORED": "FTE ignored",
    "FX_CONVERSION_MISSING": "Currency conversion missing",
    "UNAPPROVED_ADJUSTMENT": "Adjustment without approval",
    "INCOMPARABLE_GROUP": "Incomparable group",
    "UNEXPLAINED_OUTLIER_LOW": "Unexplained outlier (low)",
    "UNEXPLAINED_OUTLIER_HIGH": "Unexplained outlier (high)",
    "SYSTEMIC_DISPARITY": "Systemic disparity",
    "RATIO_MISMATCH_OTHER": "Ratio mismatch (other)",
    "ALL": "All issue types",
}

st.set_page_config(page_title="Pay Equity Review", page_icon=":bar_chart:", layout="wide")


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_csv(path, modified_time):
    """Read one CSV as text. modified_time is only there so the cache
    refreshes when the file changes."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read(path):
    return load_csv(path, os.path.getmtime(path))


def load_everything(scale):
    data = {}
    for table in schema.TABLES:
        data[table["name"]] = read(os.path.join(PROJECT_FOLDER, "data", scale, "csv", table["name"] + ".csv"))
    out_folder = os.path.join(PROJECT_FOLDER, "output", scale)
    for name in ["findings", "employee_metrics", "evaluation", "validation_summary",
                 "outlier_threshold_sweep", "evaluation_misses", "group_gap_by_role_level"]:
        data[name] = read(os.path.join(out_folder, name + ".csv"))
    data["ground_truth"] = read(os.path.join(PROJECT_FOLDER, "ground_truth", scale, "ground_truth.csv"))
    return data


def scale_is_ready(scale):
    needed = [
        os.path.join(PROJECT_FOLDER, "data", scale, "csv", "salary_record.csv"),
        os.path.join(PROJECT_FOLDER, "output", scale, "findings.csv"),
        os.path.join(PROJECT_FOLDER, "output", scale, "evaluation.csv"),
        os.path.join(PROJECT_FOLDER, "output", scale, "validation_summary.csv"),
        os.path.join(PROJECT_FOLDER, "output", scale, "group_gap_by_role_level.csv"),
    ]
    for path in needed:
        if not os.path.exists(path):
            return False
    return True


# ----------------------------------------------------------------------
# Small chart helpers
# ----------------------------------------------------------------------

def tidy(chart, height=300):
    """Shared look: quiet grid and axes so the data stands out."""
    return (chart.properties(height=height)
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor=GRID, domainColor=GREY, tickColor=GREY,
                            labelColor=INK_MUTED, titleColor=INK_MUTED, labelFontSize=12, titleFontSize=12)
            .configure_legend(labelColor="#52514e", titleColor="#52514e", orient="top"))


def horizontal_bars(frame, label_column, value_column, value_title):
    """One measure across categories: horizontal bars in a single colour."""
    bars = alt.Chart(frame).mark_bar(color=BLUE, cornerRadiusEnd=4, size=20).encode(
        x=alt.X(value_column + ":Q", title=value_title),
        y=alt.Y(label_column + ":N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        tooltip=[alt.Tooltip(label_column + ":N", title="Category"),
                 alt.Tooltip(value_column + ":Q", title=value_title)],
    )
    labels = bars.mark_text(align="left", dx=5, color="#52514e").encode(text=value_column + ":Q")
    return tidy(bars + labels, height=max(140, 36 * len(frame)))


def number(text):
    return format(int(text), ",")


# ----------------------------------------------------------------------
# Page: Overview
# ----------------------------------------------------------------------

def page_overview(data, scale):
    st.title("Pay Equity Review")
    st.caption("Synthetic company, seed " + str(config.DEFAULT_SEED) + ". Review date "
               + config.REVIEW_DATE + ". Dataset: " + scale + ".")

    evaluation = data["evaluation"]
    overall = evaluation[evaluation["issue_type"] == "ALL"].iloc[0]
    validation = data["validation_summary"]
    checks_passed = int((validation["status"] == "PASS").sum())
    active = int((data["employee"]["employment_status"] == "ACTIVE").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Employees", number(len(data["employee"])))
    col1.caption(number(active) + " active at the review date")
    col2.metric("Salary records", number(len(data["salary_record"])))
    col3.metric("Findings", number(len(data["findings"])))
    col4.metric("Quality checks passed", str(checks_passed) + " / " + str(len(validation)))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precision", format(float(overall["precision"]), ".1%"),
                help="Of everything flagged, the share that was a labelled problem.")
    col2.metric("Recall", format(float(overall["recall"]), ".1%"),
                help="Of every labelled problem, the share that was found.")
    col3.metric("Proposals", number(len(data["adjustment_proposal"])))
    col4.metric("Comparable groups", number(len(data["comparable_group"])))

    st.subheader("Findings by issue type")
    counts = data["findings"]["issue_type"].value_counts().reset_index()
    counts.columns = ["issue_type", "findings"]
    counts["Issue"] = counts["issue_type"].map(ISSUE_NAMES).fillna(counts["issue_type"])
    st.altair_chart(horizontal_bars(counts, "Issue", "findings", "Findings"), width="stretch")

    st.subheader("Detection scored against the ground truth")
    table = evaluation.copy()
    table["Issue"] = table["issue_type"].map(ISSUE_NAMES).fillna(table["issue_type"])
    table = table[["Issue", "labelled", "flagged", "true_positive", "false_positive",
                   "false_negative", "precision", "recall", "f1"]]
    table.columns = ["Issue", "Labelled", "Flagged", "Found", "Extra", "Missed", "Precision", "Recall", "F1"]
    for column in ["Labelled", "Flagged", "Found", "Extra", "Missed"]:
        table[column] = table[column].astype(int)
    for column in ["Precision", "Recall", "F1"]:
        table[column] = table[column].astype(float)
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("The five rule-based issues score 1.000 because each breaks a rule that can be checked exactly. "
               "The outlier rows are the meaningful test of the detector.")


# ----------------------------------------------------------------------
# Page: Findings
# ----------------------------------------------------------------------

def page_findings(data):
    st.title("Findings")
    st.caption("Everything the detector flagged, using the input tables only. Each finding states its evidence.")

    findings = data["findings"].copy()
    findings["Issue"] = findings["issue_type"].map(ISSUE_NAMES).fillna(findings["issue_type"])
    truth_keys = set(zip(data["ground_truth"]["issue_type"], data["ground_truth"]["record_id"]))
    labelled = []
    for issue_type, record_id in zip(findings["issue_type"], findings["record_id"]):
        labelled.append("Yes" if (issue_type, record_id) in truth_keys else "No")
    findings["In ground truth"] = labelled

    col1, col2, col3 = st.columns([2, 1, 1])
    all_issues = sorted(findings["Issue"].unique())
    chosen = col1.multiselect("Issue type", all_issues, default=all_issues)
    search = col2.text_input("Employee or record ID contains", "")
    match = col3.selectbox("In ground truth", ["All", "Yes", "No"])

    view = findings[findings["Issue"].isin(chosen)]
    if search.strip() != "":
        text = search.strip().upper()
        view = view[view["employee_id"].str.contains(text, regex=False)
                    | view["record_id"].str.contains(text, regex=False)]
    if match != "All":
        view = view[view["In ground truth"] == match]

    st.write(str(len(view)) + " of " + str(len(findings)) + " findings shown")
    shown = view[["finding_id", "Issue", "record_id", "employee_id", "recommended_action", "In ground truth"]]
    shown.columns = ["Finding", "Issue", "Record", "Employee", "Recommended action", "In ground truth"]
    st.dataframe(shown, hide_index=True, width="stretch", height=320)

    if len(view) > 0:
        st.subheader("Evidence")
        picked = st.selectbox("Choose a finding to read its evidence", list(view["finding_id"]))
        row = view[view["finding_id"] == picked].iloc[0]
        st.info(row["evidence"])
        st.write("**Issue:** " + row["Issue"] + "  \n**Record:** " + row["record_id"]
                 + "  \n**Recommended action:** " + row["recommended_action"])
        if row["employee_id"] != "":
            st.caption("To see this person's full history, open the Employee page and choose " + row["employee_id"] + ".")


# ----------------------------------------------------------------------
# Page: Employee
# ----------------------------------------------------------------------

def page_employee(data):
    st.title("Employee")
    st.caption("One person's pay history, recomputed from source records.")

    employee_ids = list(data["employee"]["employee_id"])
    flagged = sorted(set(data["findings"]["employee_id"]) - set([""]))
    only_flagged = st.checkbox("Only employees with a finding", value=True)
    options = flagged if only_flagged and len(flagged) > 0 else employee_ids
    employee_id = st.selectbox("Employee", options)

    employee = data["employee"][data["employee"]["employee_id"] == employee_id].iloc[0]
    records = data["salary_record"][data["salary_record"]["employee_id"] == employee_id]
    records = records.sort_values("effective_date")

    # Recompute the correct compa-ratio for every record with the shared formulas.
    band_rows = data["compensation_band"].to_dict("records")
    band_lookup = metrics.build_band_lookup(band_rows)
    rate_lookup = metrics.build_rate_lookup(data["fx_rate"].to_dict("records"))
    history_rows = []
    for record in records.to_dict("records"):
        band = metrics.find_band_for_date(record["role_id"], record["level_id"], record["location_id"],
                                          record["effective_date"], band_lookup)
        history_rows.append({
            "Date": record["effective_date"],
            "Reason": record["change_reason"],
            "Role": record["role_id"],
            "Level": record["level_id"],
            "Location": record["location_id"],
            "FTE": float(record["fte"]),
            "Amount": int(record["annual_amount"]),
            "Currency": record["currency_code"],
            "Band used": record["band_id"],
            "Recorded ratio": float(record["recorded_compa_ratio"]),
            "Recomputed ratio": metrics.compa_ratio(record, band, rate_lookup),
        })
    history = pd.DataFrame(history_rows)
    latest = history.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current job", latest["Role"] + " " + latest["Level"] + ", " + latest["Location"])
    col2.metric("Status", employee["employment_status"].title())
    col2.caption("Hired " + employee["hire_date"])
    metric_row = data["employee_metrics"][data["employee_metrics"]["employee_id"] == employee_id]
    if len(metric_row) > 0:
        metric = metric_row.iloc[0]
        col3.metric("Compa-ratio at review", metric["compa_ratio"])
        col3.caption(format(float(metric["residual"]), "+.4f") + " against the expected " + metric["expected_compa_ratio"])
        col4.metric("Group median", metric["group_median_compa_ratio"] or "n/a")
        if metric["group_size"] != "":
            col4.caption("Across " + str(metric["group_size"]) + " comparable employees")
    else:
        col3.metric("Compa-ratio at review", "n/a")
        col3.caption("Not active at the review date")

    st.subheader("Compa-ratio over time")
    line_data = history[["Date", "Reason", "Recomputed ratio"]].copy()
    line_data["Date"] = pd.to_datetime(line_data["Date"])
    line = alt.Chart(line_data).mark_line(color=BLUE, strokeWidth=2, interpolate="step-after").encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%b %Y", labelOverlap=True)),
        y=alt.Y("Recomputed ratio:Q", title="Compa-ratio", scale=alt.Scale(zero=False)),
    )
    points = alt.Chart(line_data).mark_circle(color=BLUE, size=90, stroke="#ffffff", strokeWidth=2).encode(
        x="Date:T", y="Recomputed ratio:Q",
        tooltip=[alt.Tooltip("Date:T", title="Date"), alt.Tooltip("Reason:N", title="Change"),
                 alt.Tooltip("Recomputed ratio:Q", title="Compa-ratio", format=".4f")],
    )
    guides = pd.DataFrame({"value": [0.80, 1.00, 1.20], "label": ["Band minimum", "Band midpoint", "Band maximum"]})
    rules = alt.Chart(guides).mark_rule(color=GREY, strokeDash=[4, 4]).encode(y="value:Q")
    rule_labels = alt.Chart(guides).mark_text(align="left", dx=4, dy=-6, color=INK_MUTED).encode(
        y="value:Q", x=alt.value(0), text="label:N")
    st.altair_chart(tidy(rules + rule_labels + line + points, height=280), width="stretch")

    st.subheader("Salary records (append-only)")
    st.dataframe(history, hide_index=True, width="stretch")
    wrong = history[(history["Recorded ratio"] - history["Recomputed ratio"]).abs() > config.RATIO_TOLERANCE]
    if len(wrong) > 0:
        st.warning(str(len(wrong)) + " record(s) have a recorded ratio that differs from the recomputed one.")

    left, right = st.columns(2)
    with left:
        st.subheader("Performance evidence")
        evidence = data["performance_evidence"][data["performance_evidence"]["employee_id"] == employee_id]
        if len(evidence) == 0:
            st.write("No evidence records.")
        else:
            evidence = evidence[["evidence_date", "evidence_type", "rating", "premium_pct"]]
            evidence.columns = ["Date", "Type", "Rating", "Premium %"]
            st.dataframe(evidence, hide_index=True, width="stretch")
    with right:
        st.subheader("Findings for this employee")
        own = data["findings"][data["findings"]["employee_id"] == employee_id]
        if len(own) == 0:
            st.write("No findings.")
        for finding in own.to_dict("records"):
            st.info("**" + ISSUE_NAMES.get(finding["issue_type"], finding["issue_type"]) + "**  \n" + finding["evidence"])

    proposals = data["adjustment_proposal"][data["adjustment_proposal"]["employee_id"] == employee_id]
    if len(proposals) > 0:
        proposal = proposals.iloc[0]
        st.subheader("Adjustment proposal " + proposal["proposal_id"] + " (" + proposal["status"] + ")")
        st.write("Proposed amount **" + number(proposal["proposed_annual_amount"]) + "**, an increase of **"
                 + proposal["increase_pct"] + "%**. " + proposal["evidence_summary"] + ".")
        trail = data["proposal_event"][data["proposal_event"]["proposal_id"] == proposal["proposal_id"]]
        trail = trail[["event_seq", "event_date", "from_status", "to_status", "actor_role"]]
        trail.columns = ["Step", "Date", "From", "To", "Actor"]
        st.dataframe(trail, hide_index=True, width="stretch")


# ----------------------------------------------------------------------
# Page: Pay distribution
# ----------------------------------------------------------------------

def page_distribution(data):
    st.title("Pay distribution")
    st.caption("Compa-ratio of active employees at the review date, after FTE and currency normalisation.")

    frame = data["employee_metrics"].copy()
    latest = data["salary_record"].set_index("salary_record_id")
    frame["role_id"] = frame["salary_record_id"].map(latest["role_id"])
    frame["level_id"] = frame["salary_record_id"].map(latest["level_id"])
    frame["location_id"] = frame["salary_record_id"].map(latest["location_id"])
    family = data["role"].set_index("role_id")["job_family"]
    frame["job_family"] = frame["role_id"].map(family)
    frame["compa_ratio"] = frame["compa_ratio"].astype(float)
    frame["residual"] = frame["residual"].astype(float)

    col1, col2, col3 = st.columns(3)
    families = col1.multiselect("Job family", sorted(frame["job_family"].unique()))
    levels = col2.multiselect("Level", sorted(frame["level_id"].unique()))
    locations = col3.multiselect("Location", sorted(frame["location_id"].unique()))
    view = frame
    if len(families) > 0:
        view = view[view["job_family"].isin(families)]
    if len(levels) > 0:
        view = view[view["level_id"].isin(levels)]
    if len(locations) > 0:
        view = view[view["location_id"].isin(locations)]

    if len(view) == 0:
        st.write("No employees match these filters.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Employees", number(len(view)))
    col2.metric("Median compa-ratio", format(view["compa_ratio"].median(), ".3f"))
    col3.metric("Below band minimum", number((view["compa_ratio"] < 0.80).sum()))
    col4.metric("Above band maximum", number((view["compa_ratio"] > 1.20).sum()))

    st.subheader("How compa-ratios are spread")
    histogram = alt.Chart(view).mark_bar(color=BLUE, cornerRadiusEnd=3).encode(
        x=alt.X("compa_ratio:Q", bin=alt.Bin(step=0.02), title="Compa-ratio (1.00 = band midpoint)"),
        y=alt.Y("count():Q", title="Employees"),
        tooltip=[alt.Tooltip("compa_ratio:Q", bin=alt.Bin(step=0.02), title="Compa-ratio"),
                 alt.Tooltip("count():Q", title="Employees")],
    )
    st.altair_chart(tidy(histogram, height=280), width="stretch")

    st.subheader("Distance from the expected ratio")
    st.caption("Each dot is one employee. Dots outside the dashed lines (more than "
               + format(config.OUTLIER_THRESHOLD, ".2f") + " from expected) are flagged as unexplained outliers, unless the person is already covered by a systemic finding.")
    names = {"": "Not flagged individually", "UNEXPLAINED_OUTLIER_LOW": "Flagged low",
             "UNEXPLAINED_OUTLIER_HIGH": "Flagged high"}
    dots_data = view.copy()
    dots_data["Flag"] = dots_data["outlier_flag"].map(names)
    dots_data["expected"] = dots_data["expected_compa_ratio"].astype(float)
    dots = alt.Chart(dots_data).mark_circle(size=28, opacity=0.6).encode(
        x=alt.X("expected:Q", title="Expected compa-ratio from documented factors", scale=alt.Scale(zero=False)),
        y=alt.Y("residual:Q", title="Actual minus expected"),
        color=alt.Color("Flag:N", title=None,
                        scale=alt.Scale(domain=["Not flagged individually", "Flagged low", "Flagged high"],
                                        range=[GREY, BLUE, ORANGE])),
        tooltip=[alt.Tooltip("employee_id:N", title="Employee"),
                 alt.Tooltip("compa_ratio:Q", title="Compa-ratio", format=".4f"),
                 alt.Tooltip("expected:Q", title="Expected", format=".4f"),
                 alt.Tooltip("residual:Q", title="Difference", format="+.4f"),
                 alt.Tooltip("Flag:N", title="Status")],
    )
    limits = pd.DataFrame({"value": [-config.OUTLIER_THRESHOLD, config.OUTLIER_THRESHOLD]})
    limit_lines = alt.Chart(limits).mark_rule(color=INK_MUTED, strokeDash=[4, 4]).encode(y="value:Q")
    st.altair_chart(tidy(dots + limit_lines, height=340), width="stretch")

    st.subheader("Median compa-ratio by level")
    by_level = view.groupby("level_id")["compa_ratio"].agg(["median", "count"]).reset_index()
    by_level.columns = ["Level", "Median compa-ratio", "Employees"]
    by_level["Median compa-ratio"] = by_level["Median compa-ratio"].round(4)
    st.dataframe(by_level, hide_index=True, width="stretch")


# ----------------------------------------------------------------------
# Page: Group comparison
# ----------------------------------------------------------------------

def page_groups(data):
    st.title("Group comparison")
    st.caption("Median compa-ratio of the two anonymous demographic groups, compared inside each role, "
               "level by level. The groups are synthetic labels with no real-world meaning.")

    gaps = data["group_gap_by_role_level"]
    compared = gaps[gaps["meets_threshold"] != ""].copy()
    flagged_roles = sorted(data["findings"][data["findings"]["issue_type"] == "SYSTEMIC_DISPARITY"]["record_id"])
    role_names = dict(zip(data["role"]["role_id"], data["role"]["role_name"]))

    st.markdown("**Rule:** a role is flagged when the same group's median is at least "
                + format(config.SYSTEMIC_GAP_PCT, ".0f") + "% lower at " + str(config.SYSTEMIC_MIN_LEVELS)
                + " or more levels, and at " + format(config.SYSTEMIC_MIN_LEVEL_SHARE, ".0%")
                + " or more of the levels that had at least " + str(config.SYSTEMIC_MIN_GROUP_SIZE)
                + " people in each group.")

    if len(compared) == 0:
        st.info("This dataset is too small to compare groups: no role and level has at least "
                + str(config.SYSTEMIC_MIN_GROUP_SIZE) + " active employees in each group. "
                "Switch to the full dataset in the sidebar.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Roles with enough data", number(compared["role_id"].nunique()))
    col2.metric("Role and level pairs compared", number(len(compared)))
    col3.metric("Roles flagged", number(len(flagged_roles)))

    # One row per role: at how many levels is Group B lower by the threshold?
    lower_group = config.DISADVANTAGED_GROUP
    summary_rows = []
    for role_id, rows in compared.groupby("role_id"):
        hits = rows[(rows["meets_threshold"] == "YES") & (rows["lower_group"] == lower_group)]
        summary_rows.append({
            "Role": role_id + " - " + role_names[role_id],
            "role_id": role_id,
            "Levels with gap": len(hits),
            "Levels compared": len(rows),
            "Result": "Flagged" if role_id in flagged_roles else "Not flagged",
        })
    summary = pd.DataFrame(summary_rows).sort_values(["Levels with gap", "Role"], ascending=[False, True])

    st.subheader("Levels where " + lower_group + " is at least "
                 + format(config.SYSTEMIC_GAP_PCT, ".0f") + "% lower, by role")
    top = summary[summary["Levels with gap"] > 0].head(15)
    if len(top) == 0:
        st.write("No role shows such a gap at any level.")
    else:
        bars = alt.Chart(top).mark_bar(cornerRadiusEnd=4, size=14).encode(
            x=alt.X("Levels with gap:Q", title="Levels with a gap", axis=alt.Axis(tickMinStep=1),
                    scale=alt.Scale(domain=[0, 5])),
            y=alt.Y("Role:N", sort=list(top["Role"]), title=None,
                    axis=alt.Axis(labelLimit=280, labelOverlap=False)),
            color=alt.Color("Result:N", title=None,
                            scale=alt.Scale(domain=["Flagged", "Not flagged"], range=[BLUE, GREY])),
            tooltip=["Role:N", "Levels with gap:Q", "Levels compared:Q", "Result:N"],
        )
        st.altair_chart(tidy(bars, height=max(160, 26 * len(top))), width="stretch")
        st.caption("Roles with one or two levels are expected by chance: with small groups, medians differ "
                   "even when pay is fair. Only a gap repeated across most levels is treated as a pattern.")

    st.subheader("Level by level")
    options = list(summary["role_id"])
    picked = st.selectbox("Role", options, format_func=lambda value: value + " - " + role_names[value])
    detail = gaps[gaps["role_id"] == picked][["level_id", "group_1_count", "group_1_median",
                                              "group_2_count", "group_2_median", "gap_pct",
                                              "lower_group", "meets_threshold"]]
    first_name = gaps["group_1"].iloc[0]
    second_name = gaps["group_2"].iloc[0]
    detail.columns = ["Level", first_name + " people", first_name + " median", second_name + " people",
                      second_name + " median", "Gap %", "Lower group", "Meets threshold"]
    st.dataframe(detail, hide_index=True, width="stretch")
    own = data["findings"][(data["findings"]["issue_type"] == "SYSTEMIC_DISPARITY")
                           & (data["findings"]["record_id"] == picked)]
    for finding in own.to_dict("records"):
        st.warning(finding["evidence"])


# ----------------------------------------------------------------------
# Page: Proposals
# ----------------------------------------------------------------------

def page_proposals(data):
    st.title("Adjustment proposals")
    st.caption("Every proposal moves through recorded steps. Decisions follow fixed rules.")

    proposals = data["adjustment_proposal"].copy()
    proposals["increase_pct"] = proposals["increase_pct"].astype(float)
    order = ["DRAFT", "SUBMITTED", "HR_REVIEWED", "REJECTED", "APPLIED"]
    counts = proposals["status"].value_counts().reindex(order).fillna(0).astype(int).reset_index()
    counts.columns = ["Status", "Proposals"]

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Where proposals stand")
        bars = alt.Chart(counts).mark_bar(color=BLUE, cornerRadiusEnd=4, size=22).encode(
            x=alt.X("Proposals:Q"), y=alt.Y("Status:N", sort=order, title=None),
            tooltip=["Status:N", "Proposals:Q"])
        labels = bars.mark_text(align="left", dx=5, color="#52514e").encode(text="Proposals:Q")
        st.altair_chart(tidy(bars + labels, height=220), width="stretch")
    with right:
        st.subheader("The rules")
        st.markdown(
            "- Rating of " + str(config.REJECT_RATING_AT_OR_BELOW) + " or lower: rejected by the HR partner\n"
            "- Increase above " + format(config.COMMITTEE_REJECT_ABOVE_PCT, ".0f") + "%: rejected by the committee\n"
            "- Increase up to " + format(config.HR_APPROVAL_LIMIT_PCT, ".0f") + "%: approved by the HR partner\n"
            "- Anything between: approved by the committee\n"
            "- An applied proposal adds a new salary record")

    col1, col2 = st.columns([1, 2])
    status = col1.multiselect("Status", order, default=order)
    low, high = col2.slider("Increase %", 0.0, float(max(40.0, proposals["increase_pct"].max())),
                            (0.0, float(max(40.0, proposals["increase_pct"].max()))))
    view = proposals[proposals["status"].isin(status)
                     & (proposals["increase_pct"] >= low) & (proposals["increase_pct"] <= high)]
    st.write(str(len(view)) + " of " + str(len(proposals)) + " proposals shown")
    shown = view[["proposal_id", "employee_id", "status", "current_compa_ratio", "target_compa_ratio",
                  "increase_pct", "proposed_annual_amount"]]
    shown.columns = ["Proposal", "Employee", "Status", "Current ratio", "Target ratio", "Increase %", "Proposed amount"]
    st.dataframe(shown, hide_index=True, width="stretch", height=280)

    if len(view) > 0:
        st.subheader("Approval trail")
        picked = st.selectbox("Choose a proposal", list(view["proposal_id"]))
        proposal = view[view["proposal_id"] == picked].iloc[0]
        st.write(proposal["evidence_summary"] + ".")
        trail = data["proposal_event"][data["proposal_event"]["proposal_id"] == picked]
        trail = trail[["event_seq", "event_date", "from_status", "to_status", "actor_role"]]
        trail.columns = ["Step", "Date", "From", "To", "Actor"]
        st.dataframe(trail, hide_index=True, width="stretch")
        statuses = list(trail["To"])
        if "APPLIED" in statuses and "APPROVED" not in statuses:
            st.error("Applied without an APPROVED step. This is the 'adjustment without approval' edge case.")


# ----------------------------------------------------------------------
# Page: Data quality
# ----------------------------------------------------------------------

def page_quality(data, scale):
    st.title("Data quality and reproducibility")

    validation = data["validation_summary"].copy()
    passed = int((validation["status"] == "PASS").sum())
    if passed == len(validation):
        st.success("All " + str(len(validation)) + " validation checks passed.")
    else:
        st.error(str(len(validation) - passed) + " of " + str(len(validation)) + " validation checks failed.")

    summary = validation.groupby("category", sort=False)["status"].agg(
        Passed=lambda values: int((values == "PASS").sum()), Total="count").reset_index()
    summary.columns = ["Category", "Passed", "Total"]
    left, right = st.columns([2, 3])
    with left:
        st.subheader("Checks by category")
        st.dataframe(summary, hide_index=True, width="stretch", height=422)
    with right:
        st.subheader("Every check")
        category = st.selectbox("Category", ["All"] + list(summary["Category"]))
        detail = validation if category == "All" else validation[validation["category"] == category]
        detail = detail[["check", "status", "records_checked", "problems"]]
        detail.columns = ["Check", "Status", "Records checked", "Problems"]
        st.dataframe(detail, hide_index=True, width="stretch", height=340)

    st.subheader("Outlier threshold: precision against recall")
    st.caption("A lower threshold finds more hidden outliers but flags more ordinary people. Current setting: "
               + format(config.OUTLIER_THRESHOLD, ".2f") + ".")
    sweep = data["outlier_threshold_sweep"].copy()
    long_rows = []
    for row in sweep.to_dict("records"):
        long_rows.append({"Threshold": float(row["threshold"]), "Measure": "Precision", "Value": float(row["precision"])})
        long_rows.append({"Threshold": float(row["threshold"]), "Measure": "Recall", "Value": float(row["recall"])})
    long_frame = pd.DataFrame(long_rows)
    base = alt.Chart(long_frame).encode(
        x=alt.X("Threshold:Q", title="Outlier threshold", scale=alt.Scale(zero=False)),
        y=alt.Y("Value:Q", title="Score", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Measure:N", title=None, scale=alt.Scale(domain=["Precision", "Recall"], range=[BLUE, ORANGE])),
    )
    lines = base.mark_line(strokeWidth=2)
    markers = base.mark_circle(size=90, stroke="#ffffff", strokeWidth=2).encode(
        tooltip=[alt.Tooltip("Measure:N"), alt.Tooltip("Threshold:Q", format=".2f"),
                 alt.Tooltip("Value:Q", title="Score", format=".3f")])
    current = alt.Chart(pd.DataFrame({"value": [config.OUTLIER_THRESHOLD]})).mark_rule(
        color=INK_MUTED, strokeDash=[4, 4]).encode(x="value:Q")
    st.altair_chart(tidy(current + lines + markers, height=280), width="stretch")

    st.subheader("Reproducibility")
    path = os.path.join(PROJECT_FOLDER, "output", scale, "reproducibility.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # Show the summary lines; keep the long checksum table folded away.
        parts = text.split("| File |")
        st.markdown(parts[0].replace("# Reproducibility check", "**Reproducibility check**"))
        if len(parts) > 1:
            with st.expander("Checksums for every file"):
                st.markdown("| File |" + parts[1])
    else:
        st.write("Run `python3 src/reproduce.py --scale " + scale + "` to create this report.")


# ----------------------------------------------------------------------
# Page: Calculator
# ----------------------------------------------------------------------

def page_calculator(data):
    st.title("Compa-ratio calculator")
    st.caption("Try the formula yourself, and see what the two classic mistakes do to the answer.")

    bands = data["compensation_band"]
    roles = data["role"]
    role_names = dict(zip(roles["role_id"], roles["role_name"]))
    currencies = sorted(data["fx_rate"]["currency_code"].unique())
    rate_lookup = metrics.build_rate_lookup(data["fx_rate"].to_dict("records"))

    col1, col2, col3, col4 = st.columns(4)
    role_id = col1.selectbox("Role", list(roles["role_id"]), format_func=lambda value: value + " - " + role_names[value])
    level_id = col2.selectbox("Level", list(data["level"]["level_id"]), index=2)
    location_id = col3.selectbox("Location", list(data["location"]["location_id"]))
    year = col4.selectbox("Band year", config.BAND_YEARS, index=len(config.BAND_YEARS) - 1)

    band = bands[(bands["role_id"] == role_id) & (bands["level_id"] == level_id)
                 & (bands["location_id"] == location_id) & (bands["band_year"] == str(year))].iloc[0]
    band_currency = band["currency_code"]

    col1, col2, col3 = st.columns(3)
    pay_currency = col1.selectbox("Paid in", currencies, index=currencies.index(band_currency))
    fte = col2.select_slider("FTE (share of full-time)", options=[0.5, 0.6, 0.8, 1.0], value=1.0)
    default_amount = int(metrics.convert_currency(int(band["band_mid"]) * fte, band_currency, pay_currency, year, rate_lookup))
    amount = col3.number_input("Annual amount actually paid", min_value=1, value=default_amount, step=1000)

    record = {"annual_amount": amount, "fte": fte, "currency_code": pay_currency,
              "effective_date": str(year) + "-06-30"}
    full_time = amount / fte
    converted = metrics.convert_currency(full_time, pay_currency, band_currency, year, rate_lookup)
    ratio = metrics.compa_ratio(record, band.to_dict(), rate_lookup)
    position = metrics.band_position(record, band.to_dict(), rate_lookup)

    st.subheader("Band " + band["band_id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Minimum", number(band["band_min"]) + " " + band_currency)
    col2.metric("Midpoint", number(band["band_mid"]) + " " + band_currency)
    col3.metric("Maximum", number(band["band_max"]) + " " + band_currency)

    st.subheader("Step by step")
    steps = pd.DataFrame([
        {"Step": "1. Divide by FTE", "Sum": format(amount, ",") + " / " + str(fte),
         "Result": format(full_time, ",.0f") + " " + pay_currency},
        {"Step": "2. Convert to the band currency", "Sum": pay_currency + " to " + band_currency + " at " + str(year) + " rates",
         "Result": format(converted, ",.0f") + " " + band_currency},
        {"Step": "3. Divide by the band midpoint", "Sum": format(converted, ",.0f") + " / " + number(band["band_mid"]),
         "Result": format(ratio, ".4f")},
    ])
    st.dataframe(steps, hide_index=True, width="stretch")

    without_fte = metrics.convert_currency(amount, pay_currency, band_currency, year, rate_lookup) / float(band["band_mid"])
    without_fx = full_time / float(band["band_mid"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Correct compa-ratio", format(ratio, ".4f"))
    col2.metric("Band position", format(position, ".2f"), help="0 = band minimum, 1 = band maximum")
    col3.metric("If FTE were ignored", format(without_fte, ".4f"))
    col3.caption("Same answer, because FTE is 1.0" if fte == 1.0 else "Wrong: part-time pay looks too low")
    col4.metric("If conversion were skipped", format(without_fx, ".4f"))
    col4.caption("Same answer, because the currencies match" if pay_currency == band_currency
                 else "Wrong: two different currencies were compared")

    if ratio < 0.80:
        st.warning("Below the band minimum.")
    elif ratio > 1.20:
        st.warning("Above the band maximum.")
    else:
        st.success("Inside the band.")


# ----------------------------------------------------------------------
# Sidebar and routing
# ----------------------------------------------------------------------

def main():
    st.sidebar.header("Pay Equity Review")
    scales = list(config.SCALES.keys())
    default_index = scales.index("full") if scale_is_ready("full") else 0
    scale = st.sidebar.selectbox("Dataset", scales, index=default_index,
                                 format_func=lambda value: value + " (" + format(config.SCALES[value], ",") + " employees)")
    page = st.sidebar.radio("Page", ["Overview", "Findings", "Employee", "Pay distribution",
                                     "Group comparison", "Proposals", "Data quality", "Calculator"])

    st.sidebar.divider()
    if st.sidebar.button("Run the pipeline again", help="Generate, validate, detect, evaluate and check reproducibility"):
        with st.spinner("Running the five steps..."):
            result = subprocess.run([sys.executable, os.path.join(PROJECT_FOLDER, "src", "run_all.py"), "--scale", scale],
                                    cwd=PROJECT_FOLDER, capture_output=True, text=True)
        st.cache_data.clear()
        if result.returncode == 0:
            st.sidebar.success("Finished. All steps passed.")
        else:
            st.sidebar.error("A step failed.")
        with st.sidebar.expander("Pipeline output"):
            st.code(result.stdout[-3000:] + result.stderr[-1000:])
    st.sidebar.caption("Fully synthetic data. The dashboard only reads files; the seed is "
                       + str(config.DEFAULT_SEED) + ".")

    if not scale_is_ready(scale):
        st.title("Pay Equity Review")
        st.warning("No results found for the '" + scale + "' dataset yet. Click 'Run the pipeline again' in the "
                   "sidebar, or run:  python3 src/run_all.py --scale " + scale)
        return

    data = load_everything(scale)
    if page == "Overview":
        page_overview(data, scale)
    elif page == "Findings":
        page_findings(data)
    elif page == "Employee":
        page_employee(data)
    elif page == "Pay distribution":
        page_distribution(data)
    elif page == "Group comparison":
        page_groups(data)
    elif page == "Proposals":
        page_proposals(data)
    elif page == "Data quality":
        page_quality(data, scale)
    else:
        page_calculator(data)


main()
