# =========================================
# file: tools/personal_finance_dashboard.py
# =========================================
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
import re
import streamlit as st

from tools.pf_visuals import cashflow_breakdown_chart, render_visual_overview


# -------------------------
# Helpers
# -------------------------
def _money(x: float) -> str:
    return f"${float(x or 0.0):,.2f}"


def _sum_df(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _download_json_button(label: str, payload: Dict, filename: str):
    s = pd.Series(payload).to_json(indent=2)
    st.download_button(
        label,
        data=s,
        file_name=filename,
        mime="application/json",
        width="stretch",
    )


def _download_csv_button(label: str, df: pd.DataFrame, filename: str):
    st.download_button(
        label,
        data=df.to_csv(index=False),
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def _norm(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _sum_by_keywords(df: pd.DataFrame, name_col: str, amount_col: str, keywords: List[str]) -> float:
    if df is None or df.empty or name_col not in df.columns or amount_col not in df.columns:
        return 0.0

    keys = [k.lower() for k in keywords]
    total = 0.0
    for _, row in df.iterrows():
        name = _norm(row.get(name_col))
        amt = pd.to_numeric(row.get(amount_col), errors="coerce")
        if pd.isna(amt):
            amt = 0.0
        if any(k in name for k in keys):
            total += float(amt)
    return float(total)


def _ensure_df(key: str, default_rows: List[Dict]) -> pd.DataFrame:
    if key not in st.session_state or not isinstance(st.session_state[key], pd.DataFrame):
        st.session_state[key] = pd.DataFrame(default_rows)
    return st.session_state[key]


def _sanitize_editor_df(df: pd.DataFrame, expected_cols: List[str], numeric_cols: List[str]) -> pd.DataFrame:
    """
    Streamlit data_editor can sometimes introduce helper columns (id/index) when adding rows.
    This normalizes the DF to the exact schema we expect.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=expected_cols)

    drop_candidates = {"id", "_id", "__id", "row_id", "_row_id", "index", "__index__"}
    extra = [c for c in df.columns if str(c).strip().lower() in drop_candidates]
    if extra:
        df = df.drop(columns=extra, errors="ignore")

    for c in expected_cols:
        if c not in df.columns:
            df[c] = "" if c not in numeric_cols else 0.0

    df = df[expected_cols].copy()

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    df = df.reset_index(drop=True)
    return df


# -------------------------
# Defaults
# -------------------------
DEFAULT_INCOME = [{"Source": "Paycheck", "Monthly Amount": 0.0, "Notes": ""}]

DEFAULT_FIXED = [
    {"Expense": "Mortgage/Rent", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Car payment", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Car insurance", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Phone", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Internet", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_VARIABLE = [
    {"Expense": "Utilities", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Groceries", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Gas/Transit", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Dining out", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Subscriptions", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "TP Fund", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Pet Expenses", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Other", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_SAVING = [
    {"Bucket": "Emergency fund", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Travel", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Fun Money", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Cash savings", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_INVESTING = [
    {"Bucket": "Brokerage", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Retirement", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "HSA", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_DEBT = [
    {"Debt": "Car loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Credit card", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Student loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Personal loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Medical debt", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
]

DEFAULT_ASSETS = [
    {"Asset": "Checking", "Value": 0.0, "Notes": ""},
    {"Asset": "Savings", "Value": 0.0, "Notes": ""},
    {"Asset": "Brokerage", "Value": 0.0, "Notes": ""},
    {"Asset": "Retirement", "Value": 0.0, "Notes": ""},
    {"Asset": "Value of Home (minus debt)", "Value": 0.0, "Notes": ""},
    {"Asset": "Value of Vehicle (minus debt)", "Value": 0.0, "Notes": ""},
]

DEFAULT_LIABILITIES = [
    {"Liability": "Mortgage", "Value": 0.0, "Notes": ""},
    {"Liability": "Car loan", "Value": 0.0, "Notes": ""},
]


# -------------------------
# Main UI
# -------------------------
def render_personal_finance_dashboard():
    st.title("💸 Personal Finance Dashboard")
    st.caption(
        "A spreadsheet-style dashboard to track monthly cash flow + net worth. "
        "Enter your numbers, click Save, and the tool does the math."
    )

    # ---- Widget defaults ----
    st.session_state.setdefault("pf_month_label", datetime.now().strftime("%B %Y"))
    st.session_state.setdefault("pf_tax_rate", 0.0)
    st.session_state.setdefault("pf_income_is", "Net (after tax)")

    # Optional gross-income breakdown defaults
    st.session_state.setdefault("pf_gross_mode", "Estimate (tax rate)")
    st.session_state.setdefault("pf_manual_taxes", 0.0)
    st.session_state.setdefault("pf_manual_retirement", 0.0)
    st.session_state.setdefault("pf_manual_match", 0.0)  # tracked only
    st.session_state.setdefault("pf_manual_benefits", 0.0)
    st.session_state.setdefault("pf_manual_other_ssi", 0.0)

    # ---- Persisted tables ----
    _ensure_df("pf_income_df", DEFAULT_INCOME)
    _ensure_df("pf_fixed_df", DEFAULT_FIXED)
    _ensure_df("pf_variable_df", DEFAULT_VARIABLE)
    _ensure_df("pf_saving_df", DEFAULT_SAVING)
    _ensure_df("pf_investing_df", DEFAULT_INVESTING)
    _ensure_df("pf_debt_df", DEFAULT_DEBT)
    _ensure_df("pf_assets_df", DEFAULT_ASSETS)
    _ensure_df("pf_liabilities_df", DEFAULT_LIABILITIES)

    # ---- Settings ----
    with st.expander("Settings", expanded=False):
        c1, c2, c3 = st.columns([1, 1, 1], gap="large")
        with c1:
            month_label = st.text_input("Month label", key="pf_month_label")
        with c2:
            tax_rate = st.number_input(
                "Estimated effective tax rate (%)",
                min_value=0.0,
                max_value=60.0,
                step=0.5,
                key="pf_tax_rate",
                help="Optional. If you enter *gross* income, this helps estimate post-tax cash flow.",
            )
        with c3:
            income_is = st.selectbox(
                "Income amounts are…",
                ["Net (after tax)", "Gross (before tax)"],
                key="pf_income_is",
            )

    # ---- Optional Gross Breakdown ----
    if income_is == "Gross (before tax)":
        st.subheader("Optional: Gross Income Breakdown")
        st.caption(
            "If you know your monthly deductions, enter them here instead of using an estimated tax rate. "
            "Company match is tracked as extra retirement contribution (it does not reduce take-home)."
        )

        st.radio(
            "How should we calculate net income?",
            ["Estimate (tax rate)", "Manual deductions"],
            key="pf_gross_mode",
            horizontal=True,
        )

        if st.session_state["pf_gross_mode"] == "Manual deductions":
            with st.form("pf_gross_breakdown_form", border=False):
                g1, g2, g3 = st.columns(3, gap="large")

                with g1:
                    st.number_input("Taxes (monthly)", min_value=0.0, step=50.0, key="pf_manual_taxes")
                    st.number_input("Benefits (monthly)", min_value=0.0, step=25.0, key="pf_manual_benefits")

                with g2:
                    st.number_input("Retirement (employee, monthly)", min_value=0.0, step=50.0, key="pf_manual_retirement")
                    st.number_input("Other/SSI (monthly)", min_value=0.0, step=25.0, key="pf_manual_other_ssi")

                with g3:
                    st.number_input(
                        "Company Match (monthly, optional)",
                        min_value=0.0,
                        step=50.0,
                        key="pf_manual_match",
                        help="Tracked as extra retirement contribution; does not reduce take-home.",
                    )

                if st.form_submit_button("Save gross breakdown", width="stretch"):
                    st.success("Saved.")
                    st.rerun()
        else:
            st.info("Using estimated tax rate. Switch to Manual deductions if you want to specify exact amounts.")

    # -------------------------
    # EDITORS
    # -------------------------
    st.subheader("Your Monthly Cash Flow")
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        tab_income, tab_exp, tab_save = st.tabs(["Income", "Expenses", "Saving/Investing"])

        with tab_income:
            st.write("Add your income sources (monthly amounts).")
            with st.form("pf_income_form", border=False):
                income_edit = st.data_editor(
                    st.session_state["pf_income_df"],
                    num_rows="dynamic",
                    hide_index=True,
                    width="stretch",
                    key="pf_income_editor",
                    column_config={
                        "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.2f"),
                    },
                )
                if st.form_submit_button("Save income", width="stretch"):
                    st.session_state["pf_income_df"] = _sanitize_editor_df(
                        income_edit,
                        expected_cols=["Source", "Monthly Amount", "Notes"],
                        numeric_cols=["Monthly Amount"],
                    )
                    st.rerun()

        with tab_exp:
            st.write("Split your expenses into fixed & variable so you can see what's flexible.")

            st.markdown("**Fixed Expenses**")
            with st.form("pf_fixed_form", border=False):
                fixed_edit = st.data_editor(
                    st.session_state["pf_fixed_df"],
                    num_rows="dynamic",
                    hide_index=True,
                    width="stretch",
                    key="pf_fixed_editor",
                    column_config={
                        "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                    },
                )
                if st.form_submit_button("Save fixed expenses", width="stretch"):
                    st.session_state["pf_fixed_df"] = _sanitize_editor_df(
                        fixed_edit,
                        expected_cols=["Expense", "Monthly Amount", "Notes"],
                        numeric_cols=["Monthly Amount"],
                    )
                    st.rerun()

            st.markdown("**Variable Expenses**")
            with st.form("pf_variable_form", border=False):
                variable_edit = st.data_editor(
                    st.session_state["pf_variable_df"],
                    num_rows="dynamic",
                    hide_index=True,
                    width="stretch",
                    key="pf_variable_editor",
                    column_config={
                        "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                    },
                )
                if st.form_submit_button("Save variable expenses", width="stretch"):
                    st.session_state["pf_variable_df"] = _sanitize_editor_df(
                        variable_edit,
                        expected_cols=["Expense", "Monthly Amount", "Notes"],
                        numeric_cols=["Monthly Amount"],
                    )
                    st.rerun()

        with tab_save:
            st.write("Monthly contributions you want to make.")
            s_col, i_col = st.columns(2, gap="large")

            with s_col:
                st.markdown("**Saving**")
                with st.form("pf_saving_form", border=False):
                    saving_edit = st.data_editor(
                        st.session_state["pf_saving_df"],
                        num_rows="dynamic",
                        hide_index=True,
                        width="stretch",
                        key="pf_saving_editor",
                        column_config={
                            "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                        },
                    )
                    if st.form_submit_button("Save saving", width="stretch"):
                        st.session_state["pf_saving_df"] = _sanitize_editor_df(
                            saving_edit,
                            expected_cols=["Bucket", "Monthly Amount", "Notes"],
                            numeric_cols=["Monthly Amount"],
                        )
                        st.rerun()

            with i_col:
                st.markdown("**Investing**")
                with st.form("pf_investing_form", border=False):
                    investing_edit = st.data_editor(
                        st.session_state["pf_investing_df"],
                        num_rows="dynamic",
                        hide_index=True,
                        width="stretch",
                        key="pf_investing_editor",
                        column_config={
                            "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                        },
                    )
                    if st.form_submit_button("Save investing", width="stretch"):
                        st.session_state["pf_investing_df"] = _sanitize_editor_df(
                            investing_edit,
                            expected_cols=["Bucket", "Monthly Amount", "Notes"],
                            numeric_cols=["Monthly Amount"],
                        )
                        st.rerun()

    # -------------------------
    # CALCULATIONS
    # -------------------------
    income_df = st.session_state["pf_income_df"]
    fixed_df = st.session_state["pf_fixed_df"]
    variable_df = st.session_state["pf_variable_df"]
    saving_df = st.session_state["pf_saving_df"]
    investing_df = st.session_state["pf_investing_df"]
    debt_df = st.session_state["pf_debt_df"]
    assets_df = st.session_state["pf_assets_df"]
    liabilities_df = st.session_state["pf_liabilities_df"]

    total_income = _sum_df(income_df, "Monthly Amount")

    est_tax = 0.0
    manual_deductions_total = 0.0
    net_income = total_income

    if income_is == "Gross (before tax)":
        if st.session_state.get("pf_gross_mode") == "Estimate (tax rate)":
            if float(tax_rate) > 0:
                est_tax = total_income * (float(tax_rate) / 100.0)
            net_income = total_income - est_tax
        else:
            manual_taxes = float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0)
            manual_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
            manual_benefits = float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0)
            manual_other_ssi = float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0)
            manual_deductions_total = manual_taxes + manual_retirement + manual_benefits + manual_other_ssi
            net_income = total_income - manual_deductions_total

    fixed_total = _sum_df(fixed_df, "Monthly Amount")
    variable_total = _sum_df(variable_df, "Monthly Amount")
    expenses_total = fixed_total + variable_total

    saving_total = _sum_df(saving_df, "Monthly Amount")
    investing_total = _sum_df(investing_df, "Monthly Amount")

    investing_display = investing_total
    investing_cashflow = investing_total

    manual_retirement = 0.0
    company_match = 0.0

    if income_is == "Gross (before tax)" and st.session_state.get("pf_gross_mode") == "Manual deductions":
        manual_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
        company_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)
        investing_display = investing_total + manual_retirement + company_match
        investing_cashflow = investing_total + manual_retirement

    total_monthly_debt_payments = _sum_df(debt_df, "Monthly Payment")
    total_saving_and_investing_cashflow = saving_total + investing_cashflow

    total_outflow = expenses_total + total_saving_and_investing_cashflow + total_monthly_debt_payments
    remaining = net_income - total_outflow

    total_assets = _sum_df(assets_df, "Value")
    total_liabilities = _sum_df(liabilities_df, "Value")
    net_worth = total_assets - total_liabilities

    employee_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
    company_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)
    total_retirement_contrib = employee_retirement + company_match

    # -------------------------
    # SNAPSHOT CHART
    # -------------------------
    # st.subheader("This Month at a Glance")
    # fig, _, _ = cashflow_breakdown_chart(
    #     net_income=net_income,
    #     living_expenses=expenses_total,
    #     debt_payments=total_monthly_debt_payments,
    #     saving=saving_total,
    #     investing_cashflow=investing_cashflow,
    # )
    # st.plotly_chart(fig, width="stretch")

    # -------------------------
    # VISUAL OVERVIEW
    # -------------------------
    render_visual_overview(
        expenses_total=expenses_total,
        total_monthly_debt_payments=total_monthly_debt_payments,
        saving_total=saving_total,
        investing_cashflow=investing_cashflow,
        remaining=remaining,
        fixed_df=fixed_df,
        variable_df=variable_df,
        debt_df=debt_df,
    )

    # ---- Emergency Minimum ----
    ESSENTIAL_VARIABLE_KEYWORDS = [
        "grocery", "groceries",
        "electric", "electricity", "natural gas", "water", "sewer", "trash", "garbage",
        "utility", "utilities",
        "internet", "wifi", "phone", "cell",
        "insurance", "medical", "health", "prescription", "rx", "medicine",
    ]

    essential_variable = _sum_by_keywords(
        variable_df,
        name_col="Expense",
        amount_col="Monthly Amount",
        keywords=ESSENTIAL_VARIABLE_KEYWORDS,
    )

    debt_minimums = total_monthly_debt_payments
    emergency_minimum_monthly = fixed_total + essential_variable + debt_minimums

    # ---- Summary UI ----
    def _section(title: str):
        st.markdown(
            f"<div style='font-size:0.85rem; letter-spacing:.06em; text-transform:uppercase; opacity:.70; margin: 0.2rem 0 0.6rem 0;'>{title}</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("### Summary")

        # -------------------------
        # SNAPSHOT CHART
        # -------------------------
        st.subheader("This Month at a Glance")
        fig, _, _ = cashflow_breakdown_chart(
            net_income=net_income,
            living_expenses=expenses_total,
            debt_payments=total_monthly_debt_payments,
            saving=saving_total,
            investing_cashflow=investing_cashflow,
        )
        st.plotly_chart(fig, width="stretch")

        with st.container(border=True):
            _section("Income")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Net Income", _money(net_income))
            c2.metric("Gross Income", _money(total_income))

        st.write("")

        with st.container(border=True):
            _section("Outflows")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Living Expenses", _money(expenses_total))
            c2.metric("Debt Payments", _money(total_monthly_debt_payments))

            c3, c4 = st.columns(2, gap="medium")
            c3.metric("Saving", _money(saving_total))
            c4.metric("Investing", _money(investing_display))

            c5, c6 = st.columns(2, gap="medium")
            c5.metric("Total Expenses", _money(total_outflow))
            c6.metric("Remaining", _money(net_income - total_outflow))

        st.write("")

        with st.container(border=True):
            _section("Remaining")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Monthly", _money(remaining))
            c2.metric("Weekly", _money(remaining / 4.33))
            c3, _ = st.columns(2, gap="medium")
            c3.metric("Daily", _money(remaining / 30.4))

        st.write("")

        with st.container(border=True):
            _section("Net Worth")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Net Worth", _money(net_worth))
            c2.metric("Total Liabilities", _money(total_liabilities))

    st.divider()
    st.subheader("🆘 Your Emergency Minimum")

    e1, e2, e3, e4 = st.columns(4, gap="large")
    e1.metric("Emergency Minimum (monthly)", _money(emergency_minimum_monthly))
    e2.metric("3 months", _money(emergency_minimum_monthly * 3))
    e3.metric("6 months", _money(emergency_minimum_monthly * 6))
    e4.metric("12 months", _money(emergency_minimum_monthly * 12))

    st.write("Your emergency minimum covers:")
    st.write(f"• **Fixed bills** (everything in your fixed expenses): {_money(fixed_total)}")
    st.write(f"• **Essentials** (groceries, utilities, healthcare): {_money(essential_variable)}")
    st.write(f"• **Debt payments** you must make: {_money(debt_minimums)}")

    st.divider()

    # ---- Net worth section ----
    st.subheader("Your Net Worth")

    a_col, l_col = st.columns([1, 1], gap="large")

    with a_col:
        st.markdown("**Assets**")
        with st.form("pf_assets_form", border=False):
            assets_edit = st.data_editor(
                st.session_state["pf_assets_df"],
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                key="pf_assets_editor",
                column_config={
                    "Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
                },
            )
            if st.form_submit_button("Save assets", width="stretch"):
                st.session_state["pf_assets_df"] = _sanitize_editor_df(
                    assets_edit,
                    expected_cols=["Asset", "Value", "Notes"],
                    numeric_cols=["Value"],
                )
                st.rerun()

    with l_col:
        st.markdown("**Liabilities**")
        with st.form("pf_liabilities_form", border=False):
            liabilities_edit = st.data_editor(
                st.session_state["pf_liabilities_df"],
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                key="pf_liabilities_editor",
                column_config={
                    "Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
                },
            )
            if st.form_submit_button("Save liabilities", width="stretch"):
                st.session_state["pf_liabilities_df"] = _sanitize_editor_df(
                    liabilities_edit,
                    expected_cols=["Liability", "Value", "Notes"],
                    numeric_cols=["Value"],
                )
                st.rerun()

    n1, n2, n3 = st.columns(3, gap="large")
    n1.metric("Total Assets", _money(total_assets))
    n2.metric("Total Liabilities", _money(total_liabilities))
    n3.metric("Net Worth", _money(net_worth))

    st.divider()

    # ---- Debt info ----
    st.subheader("Debt Details")
    st.caption("This doesn't affect net worth beyond the liability values, it's just here for clarity and planning.")

    with st.form("pf_debt_form", border=False):
        debt_edit = st.data_editor(
            st.session_state["pf_debt_df"],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="pf_debt_editor",
            column_config={
                "Balance": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
                "APR %": st.column_config.NumberColumn(min_value=0.0, max_value=60.0, step=0.1, format="%.2f"),
                "Monthly Payment": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
            },
        )
        if st.form_submit_button("Save debt details", width="stretch"):
            st.session_state["pf_debt_df"] = _sanitize_editor_df(
                debt_edit,
                expected_cols=["Debt", "Balance", "APR %", "Monthly Payment", "Notes"],
                numeric_cols=["Balance", "APR %", "Monthly Payment"],
            )
            st.rerun()

    st.metric("Total Monthly Debt Payments", _money(total_monthly_debt_payments))

    st.divider()

    # ---- Exports & snapshot ----
    st.subheader("Export/Save Snapshot")

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "month_label": month_label,
        "settings": {
            "income_is": income_is,
            "tax_rate_pct": float(tax_rate),
            "gross_mode": st.session_state.get("pf_gross_mode"),
        },
        "gross_breakdown_optional": {
            "taxes": float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0),
            "retirement_employee": float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0),
            "company_match": float(st.session_state.get("pf_manual_match", 0.0) or 0.0),
            "benefits": float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0),
            "other_ssi": float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0),
        },
        "monthly_cash_flow": {
            "total_income_entered": float(total_income),
            "estimated_taxes": float(est_tax),
            "manual_deductions_total": float(manual_deductions_total),
            "net_income": float(net_income),
            "fixed_expenses": float(fixed_total),
            "variable_expenses": float(variable_total),
            "debt_payments_monthly": float(total_monthly_debt_payments),
            "total_expenses": float(expenses_total),
            "saving_monthly": float(saving_total),
            "investing_monthly": float(investing_display),
            "investing_manual_retirement": float(manual_retirement),
            "investing_company_match": float(company_match),
            "saving_and_investing_cashflow_total": float(total_saving_and_investing_cashflow),
            "left_over": float(remaining),
            "safe_to_spend_weekly": float(remaining / 4.33),
            "safe_to_spend_daily": float(remaining / 30.4),
            "retirement_total_employee_plus_match": float(total_retirement_contrib),
        },
        "net_worth": {
            "assets_total": float(total_assets),
            "liabilities_total": float(total_liabilities),
            "net_worth": float(net_worth),
        },
        "tables": {
            "income": st.session_state["pf_income_df"].to_dict(orient="records"),
            "fixed_expenses": st.session_state["pf_fixed_df"].to_dict(orient="records"),
            "variable_expenses": st.session_state["pf_variable_df"].to_dict(orient="records"),
            "saving": st.session_state["pf_saving_df"].to_dict(orient="records"),
            "investing": st.session_state["pf_investing_df"].to_dict(orient="records"),
            "assets": st.session_state["pf_assets_df"].to_dict(orient="records"),
            "liabilities": st.session_state["pf_liabilities_df"].to_dict(orient="records"),
            "debt_details": st.session_state["pf_debt_df"].to_dict(orient="records"),
        },
        "emergency_minimum": {
            "monthly": float(emergency_minimum_monthly),
            "fixed_included": float(fixed_total),
            "essential_variable_included": float(essential_variable),
            "debt_minimums_included": float(debt_minimums),
            "keywords_used": ESSENTIAL_VARIABLE_KEYWORDS,
        },
    }

    cA, cB, cC = st.columns(3, gap="large")
    with cA:
        _download_json_button("Download snapshot (JSON)", snapshot, "personal_finance_snapshot.json")
    with cB:
        combined = pd.concat(
            [
                st.session_state["pf_income_df"].assign(Table="Income"),
                st.session_state["pf_fixed_df"].assign(Table="Fixed Expenses"),
                st.session_state["pf_variable_df"].assign(Table="Variable Expenses"),
                st.session_state["pf_saving_df"].assign(Table="Saving"),
                st.session_state["pf_investing_df"].assign(Table="Investing"),
            ],
            ignore_index=True,
            sort=False,
        )
        _download_csv_button("Download monthly tables (CSV)", combined, "personal_finance_monthly_tables.csv")
    with cC:
        nw_combined = pd.concat(
            [
                st.session_state["pf_assets_df"].rename(columns={"Asset": "Item"}).assign(Type="Asset"),
                st.session_state["pf_liabilities_df"].rename(columns={"Liability": "Item"}).assign(Type="Liability"),
            ],
            ignore_index=True,
            sort=False,
        )
        _download_csv_button("Download net worth tables (CSV)", nw_combined, "personal_finance_net_worth_tables.csv")

    with st.expander("Reset all data", expanded=False):
        st.warning("This clears the tool’s saved tables in this session.")
        if st.button("Reset now", type="primary", key="pf_reset_btn", width="stretch"):
            for k in list(st.session_state.keys()):
                if k.startswith("pf_"):
                    del st.session_state[k]
            st.rerun()