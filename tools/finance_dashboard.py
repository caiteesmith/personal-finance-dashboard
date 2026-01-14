# =========================================
# file: tools/finance_dashboard.py
# =========================================
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import json
import pandas as pd
import re
import streamlit as st
import hashlib

from tools.pf_visuals import (
    cashflow_breakdown_chart,
    render_visual_overview,
    debt_burden_indicator,
    debt_payoff_order_chart,
)

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


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1f}%"


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _load_snapshot_into_state(snapshot: dict):
    """
    Loads snapshot data into st.session_state.
    IMPORTANT: This should load ONLY non-widget-backed keys (tables + pf_manual_* + simple settings).
    Draft widget keys (pf_draft_*) are set in _apply_pending_snapshot_if_any BEFORE widgets exist.
    """
    if not isinstance(snapshot, dict):
        return

    # ---- Settings (optional) ----
    st.session_state["pf_month_label"] = snapshot.get("month_label", st.session_state.get("pf_month_label"))

    settings = snapshot.get("settings", {}) or {}
    if "income_is" in settings:
        st.session_state["pf_income_is"] = settings.get("income_is") or st.session_state.get("pf_income_is", "Net (after tax)")
    if "gross_mode" in settings:
        st.session_state["pf_gross_mode"] = settings.get("gross_mode") or st.session_state.get("pf_gross_mode", "Estimate (tax rate)")
    if "tax_rate_pct" in settings:
        st.session_state["pf_tax_rate"] = _safe_float(settings.get("tax_rate_pct", st.session_state.get("pf_tax_rate", 0.0)))

    # ---- Gross breakdown (saved values used by calcs) ----
    gb = snapshot.get("gross_breakdown_optional", {}) or {}
    st.session_state["pf_manual_taxes"] = _safe_float(gb.get("taxes", 0))
    st.session_state["pf_manual_retirement"] = _safe_float(gb.get("retirement_employee", 0))
    st.session_state["pf_manual_match"] = _safe_float(gb.get("company_match", 0))
    st.session_state["pf_manual_benefits"] = _safe_float(gb.get("benefits", 0))
    st.session_state["pf_manual_other_ssi"] = _safe_float(gb.get("other_ssi", 0))

    # ---- Tables ----
    tables = snapshot.get("tables", {}) or {}

    def _set_table(key: str, rows: list[dict], expected_cols: list[str], numeric_cols: list[str]):
        df = pd.DataFrame(rows or [])
        st.session_state[key] = _sanitize_editor_df(df, expected_cols=expected_cols, numeric_cols=numeric_cols)

    _set_table("pf_income_df", tables.get("income"), ["Source", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_fixed_df", tables.get("fixed_expenses"), ["Expense", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_variable_df", tables.get("variable_expenses"), ["Expense", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_saving_df", tables.get("saving"), ["Bucket", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_investing_df", tables.get("investing"), ["Bucket", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_assets_df", tables.get("assets"), ["Asset", "Value", "Notes"], ["Value"])
    _set_table("pf_liabilities_df", tables.get("liabilities"), ["Liability", "Value", "Notes"], ["Value"])
    _set_table(
        "pf_debt_df",
        tables.get("debt_details"),
        ["Debt", "Balance", "APR %", "Monthly Payment", "Notes"],
        ["Balance", "APR %", "Monthly Payment"],
    )

    def _dashboard_header(net_income, total_outflow, remaining, emergency_minimum_monthly, net_worth, debt_payments):
        with st.container(border=True):
            a, b, c, d, e, f = st.columns(6, gap="medium")
            a.metric("Net", _money(net_income))
            b.metric("Outflow", _money(total_outflow))
            c.metric("Leftover", _money(remaining))
            d.metric("Emergency Min", _money(emergency_minimum_monthly))
            e.metric("Net Worth", _money(net_worth))
            f.metric("Debt Min", _money(debt_payments))


# -------------------------
# Defaults
# -------------------------
DEFAULT_INCOME = [
    {"Source": "Paycheck 1", "Monthly Amount": 0.0, "Notes": ""},
    {"Source": "Paycheck 2", "Monthly Amount": 0.0, "Notes": ""},
]

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
    {"Expense": "Prescriptions", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Childcare", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Gym/Fitness", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "TP Fund", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Pet Expenses", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Other", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_SAVING = [
    {"Bucket": "Emergency fund", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Entertainment", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Travel", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Gifts", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Cash savings", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_INVESTING = [
    {"Bucket": "Brokerage", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "401k", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "403b", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Traditional IRA", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Roth IRA", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "529", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "HSA", "Monthly Amount": 0.0, "Notes": ""},
]

DEFAULT_DEBT = [
    {"Debt": "Car loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Credit card", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Student loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Personal loan", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "Medical debt", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
    {"Debt": "HELOC", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
]

DEFAULT_ASSETS = [
    {"Asset": "Checking", "Value": 0.0, "Notes": ""},
    {"Asset": "Savings", "Value": 0.0, "Notes": ""},
    {"Asset": "HYSA", "Value": 0.0, "Notes": ""},
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
    def _apply_pending_snapshot_if_any():
        if not st.session_state.get("pf_has_pending_import"):
            return

        snap = st.session_state.get("pf_pending_snapshot")
        if not isinstance(snap, dict):
            st.session_state["pf_has_pending_import"] = False
            st.session_state.pop("pf_pending_snapshot", None)
            return

        # ✅ Load tables + saved (pf_manual_*) + settings
        _load_snapshot_into_state(snap)

        # ✅ Set draft widget keys BEFORE widgets are instantiated
        gb = snap.get("gross_breakdown_optional", {}) or {}
        st.session_state["pf_draft_taxes"] = _safe_float(gb.get("taxes", 0))
        st.session_state["pf_draft_retirement"] = _safe_float(gb.get("retirement_employee", 0))
        st.session_state["pf_draft_benefits"] = _safe_float(gb.get("benefits", 0))
        st.session_state["pf_draft_other_ssi"] = _safe_float(gb.get("other_ssi", 0))
        st.session_state["pf_draft_match"] = _safe_float(gb.get("company_match", 0))

        # Clear pending import
        st.session_state["pf_has_pending_import"] = False
        st.session_state.pop("pf_pending_snapshot", None)

    # 🔥 must run before ANY widgets are created
    _apply_pending_snapshot_if_any()

    st.session_state.setdefault("pf_uploader_nonce", 0)
    st.session_state.setdefault("pf_last_import_sig", "")

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

    # New: toggle for paycheck breakdown mode
    st.session_state.setdefault("pf_use_gross_breakdown", False)

    # ---- Persisted tables ----
    _ensure_df("pf_income_df", DEFAULT_INCOME)
    _ensure_df("pf_fixed_df", DEFAULT_FIXED)
    _ensure_df("pf_variable_df", DEFAULT_VARIABLE)
    _ensure_df("pf_saving_df", DEFAULT_SAVING)
    _ensure_df("pf_investing_df", DEFAULT_INVESTING)
    _ensure_df("pf_debt_df", DEFAULT_DEBT)
    _ensure_df("pf_assets_df", DEFAULT_ASSETS)
    _ensure_df("pf_liabilities_df", DEFAULT_LIABILITIES)

    # ---- Read settings from session_state for calculations ----
    month_label = st.session_state.get("pf_month_label", datetime.now().strftime("%B %Y"))
    tax_rate = float(st.session_state.get("pf_tax_rate", 0.0) or 0.0)
    income_is = st.session_state.get("pf_income_is", "Net (after tax)")
    gross_mode = st.session_state.get("pf_gross_mode", "Estimate (tax rate)")
    use_paycheck_breakdown = bool(st.session_state.get("pf_use_gross_breakdown", False))

    # -------------------------
    # CALCULATIONS (moved up so we can show a header + callouts early)
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

    manual_taxes = float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0)
    manual_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
    manual_benefits = float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0)
    manual_other_ssi = float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0)
    employer_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)

    manual_deductions_total = manual_taxes + manual_retirement + manual_benefits + manual_other_ssi

    # ✅ Net income respects the toggle
    net_income = total_income - manual_deductions_total if use_paycheck_breakdown else total_income

    est_tax = 0.0  # still here in case you add estimated tax mode back later

    fixed_total = _sum_df(fixed_df, "Monthly Amount")
    variable_total = _sum_df(variable_df, "Monthly Amount")
    expenses_total = fixed_total + variable_total

    saving_total = _sum_df(saving_df, "Monthly Amount")
    investing_total = _sum_df(investing_df, "Monthly Amount")

    investing_cashflow = investing_total  # take-home only
    investing_display = investing_total + manual_retirement + employer_match  # includes payroll + match

    total_monthly_debt_payments = _sum_df(debt_df, "Monthly Payment")
    total_saving_and_investing_cashflow = saving_total + investing_cashflow

    total_outflow = expenses_total + total_saving_and_investing_cashflow + total_monthly_debt_payments
    remaining = net_income - total_outflow
    has_debt = total_monthly_debt_payments > 0

    total_assets = _sum_df(assets_df, "Value")
    total_liabilities = _sum_df(liabilities_df, "Value")
    net_worth = total_assets - total_liabilities

    employee_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
    company_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)
    total_retirement_contrib = employee_retirement + company_match

    investing_rate_of_gross = (investing_display / total_income) * 100 if total_income > 0 else None
    investing_rate_of_net = (investing_display / net_income) * 100 if net_income > 0 else None

    # ---- Emergency Minimum + Needs/Wants/Save Split ----
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

    needs_total = emergency_minimum_monthly
    wants_total = max(variable_total - essential_variable, 0.0)
    save_invest_total = saving_total + investing_cashflow
    unallocated_total = max(remaining, 0.0)

    needs_pct = wants_pct = save_invest_pct = unallocated_pct = None
    if net_income > 0:
        needs_pct = (needs_total / net_income) * 100
        wants_pct = (wants_total / net_income) * 100
        save_invest_pct = (save_invest_total / net_income) * 100
        unallocated_pct = max(0.0, 100 - (needs_pct + wants_pct + save_invest_pct))

    # -------------------------
    # TOP PAGE UI
    # -------------------------
    st.title("💸 Personal Finance Dashboard")
    st.caption(
        "A spreadsheet-style dashboard to track your personal monthly cash flow and net worth. "
        "Enter your numbers and the tool does the math."
    )

    def _dashboard_header():
        with st.container(border=True):
            a, b, c, d, e, f = st.columns(6, gap="medium")
            a.metric("Net", _money(net_income))
            b.metric("Outflow", _money(total_outflow))
            c.metric("Leftover", _money(remaining))
            d.metric("Emergency Min", _money(emergency_minimum_monthly))
            e.metric("Net Worth", _money(net_worth))
            f.metric("Debt Min", _money(total_monthly_debt_payments))

    _dashboard_header()

    st.divider()

    # ---- Small helper: editor that "auto-saves" into session_state ----
    def _edit_table(title: str, state_key: str, editor_key: str, expected_cols: list[str], numeric_cols: list[str], column_config=None, caption: str | None = None):
        st.markdown(f"**{title}**")
        if caption:
            st.caption(caption)

        edited = st.data_editor(
            st.session_state[state_key],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key=editor_key,
            column_config=column_config or {},
        )
        st.session_state[state_key] = _sanitize_editor_df(
            edited,
            expected_cols=expected_cols,
            numeric_cols=numeric_cols,
        )
        st.write("")

    # -------------------------
    # MAIN: Inputs (left) + Summary (right)
    # -------------------------
    st.subheader("Your Monthly Cash Flow")
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        tab_income, tab_exp, tab_save = st.tabs(["Income", "Expenses", "Saving/Investing"])

        with tab_income:
            st.write("Add your income sources. If you have a two-income household, include both here.")

            _edit_table(
                title="Income",
                state_key="pf_income_df",
                editor_key="pf_income_editor",
                expected_cols=["Source", "Monthly Amount", "Notes"],
                numeric_cols=["Monthly Amount"],
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.2f"),
                },
                caption="Tip: enter monthly totals. (Example: biweekly paycheck × 2.15.)",
            )

            # ✅ Toggle instead of expander always open
            st.markdown("---")
            st.markdown("#### Optional: Paycheck breakdown (gross → net)")
            st.caption(
                "Turn this on only if the income you entered above is **gross** and you want the dashboard to calculate "
                "**net income** using monthly deductions (taxes, benefits, retirement)."
            )

            use_paycheck_breakdown = st.toggle(
                "Use paycheck breakdown",
                value=st.session_state.get("pf_use_gross_breakdown", False),
                key="pf_use_gross_breakdown",
            )

            if use_paycheck_breakdown:
                st.session_state.setdefault("pf_draft_taxes", float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0))
                st.session_state.setdefault("pf_draft_retirement", float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0))
                st.session_state.setdefault("pf_draft_benefits", float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0))
                st.session_state.setdefault("pf_draft_other_ssi", float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0))
                st.session_state.setdefault("pf_draft_match", float(st.session_state.get("pf_manual_match", 0.0) or 0.0))

                g1, g2, g3 = st.columns(3, gap="large")
                with g1:
                    st.number_input("Taxes", min_value=0.0, step=50.0, key="pf_draft_taxes")
                    st.number_input("Benefits", min_value=0.0, step=25.0, key="pf_draft_benefits")
                with g2:
                    st.number_input("Retirement (employee)", min_value=0.0, step=50.0, key="pf_draft_retirement")
                    st.number_input("Other/SSI", min_value=0.0, step=25.0, key="pf_draft_other_ssi")
                with g3:
                    st.number_input(
                        "Company Match (optional)",
                        min_value=0.0,
                        step=50.0,
                        key="pf_draft_match",
                        help="Tracked as extra retirement contribution; does not reduce take-home.",
                    )

                if st.button("Save breakdown", type="primary", width="stretch"):
                    st.session_state["pf_manual_taxes"] = float(st.session_state["pf_draft_taxes"] or 0.0)
                    st.session_state["pf_manual_benefits"] = float(st.session_state["pf_draft_benefits"] or 0.0)
                    st.session_state["pf_manual_retirement"] = float(st.session_state["pf_draft_retirement"] or 0.0)
                    st.session_state["pf_manual_other_ssi"] = float(st.session_state["pf_draft_other_ssi"] or 0.0)
                    st.session_state["pf_manual_match"] = float(st.session_state["pf_draft_match"] or 0.0)
                    st.success("Saved.")
                    st.rerun()

                with st.expander("See saved deductions being used", expanded=False):
                    st.write(f"Taxes: **{_money(st.session_state.get('pf_manual_taxes', 0.0))}**")
                    st.write(f"Benefits: **{_money(st.session_state.get('pf_manual_benefits', 0.0))}**")
                    st.write(f"Retirement: **{_money(st.session_state.get('pf_manual_retirement', 0.0))}**")
                    st.write(f"Other/SSI: **{_money(st.session_state.get('pf_manual_other_ssi', 0.0))}**")
                    st.caption("Company match doesn’t reduce take-home; it’s tracked separately.")
                    st.write(f"Company Match (tracked): **{_money(st.session_state.get('pf_manual_match', 0.0))}**")

        with tab_exp:
            _edit_table(
                title="Fixed Expenses",
                state_key="pf_fixed_df",
                editor_key="pf_fixed_editor",
                expected_cols=["Expense", "Monthly Amount", "Notes"],
                numeric_cols=["Monthly Amount"],
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                },
                caption="Fixed = bills that are predictable each month.",
            )

            _edit_table(
                title="Variable Expenses",
                state_key="pf_variable_df",
                editor_key="pf_variable_editor",
                expected_cols=["Expense", "Monthly Amount", "Notes"],
                numeric_cols=["Monthly Amount"],
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                },
                caption="Variable = things that change (utilities, groceries, dining, etc.).",
            )

        with tab_save:
            st.write("Monthly contributions you want to make.")
            s_col, i_col = st.columns(2, gap="large")

            with s_col:
                _edit_table(
                    title="Saving",
                    state_key="pf_saving_df",
                    editor_key="pf_saving_editor",
                    expected_cols=["Bucket", "Monthly Amount", "Notes"],
                    numeric_cols=["Monthly Amount"],
                    column_config={
                        "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                    },
                )

            with i_col:
                _edit_table(
                    title="Investing",
                    state_key="pf_investing_df",
                    editor_key="pf_investing_editor",
                    expected_cols=["Bucket", "Monthly Amount", "Notes"],
                    numeric_cols=["Monthly Amount"],
                    column_config={
                        "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                    },
                )

    # ---- Summary UI helpers ----
    def _section(title: str):
        st.markdown(
            f"<div style='font-size:0.85rem; letter-spacing:.06em; text-transform:uppercase; opacity:.70; margin: 0.2rem 0 0.6rem 0;'>{title}</div>",
            unsafe_allow_html=True,
        )

    with right:
        # ✅ One container, less “box fatigue”
        with st.container(border=True):
            st.markdown("### Summary")
            st.caption("This updates based on what you enter on the left.")

            st.subheader("This Month at a Glance")
            fig, _, _ = cashflow_breakdown_chart(
                net_income=net_income,
                living_expenses=expenses_total,
                debt_payments=total_monthly_debt_payments,
                saving=saving_total,
                investing_cashflow=investing_cashflow,
            )
            st.plotly_chart(fig, width="stretch")

            st.divider()
            _section("Income")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Net Income", _money(net_income))
            c2.metric("Gross Income", _money(total_income))

            st.divider()
            _section("Expenses & Investing")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Living Expenses", _money(expenses_total))
            c2.metric("Debt Payments", _money(total_monthly_debt_payments))

            c3, c4 = st.columns(2, gap="medium")
            c3.metric("Saving", _money(saving_total))
            c4.metric("Investing (incl. retirement)", _money(investing_display))

            st.divider()
            _section("Leftover")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Monthly", _money(remaining))
            c2.metric("Weekly", _money(remaining / 4.33))

            with st.expander("What you can do with leftover", expanded=False):
                st.caption("Totally optional guidance — use what fits your goals and your season of life.")
                if remaining <= 0:
                    st.info("You’re allocating basically everything. If it feels tight, trim wants first or temporarily lower saving/investing.")
                else:
                    st.markdown(f"**You have {_money(remaining)} available each month.** Ideas:")
                    bullets = [
                        "Build/boost savings (emergency fund, sinking funds, short-term goals).",
                        "Invest more (brokerage, retirement, HSA if relevant).",
                        "Spend intentionally (guilt-free fun money that’s already accounted for).",
                        "Hold it as a buffer for a month while you watch patterns.",
                    ]
                    if has_debt:
                        bullets.insert(2, "Pay down debt faster (extra toward highest-interest balance).")
                    for b in bullets:
                        st.markdown(f"- {b}")

            st.divider()
            _section("Spending & Saving Split")
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            c1.metric("Needs", _pct(needs_pct))
            c2.metric("Wants", _pct(wants_pct))
            c3.metric("Save+Invest", _pct(save_invest_pct))
            c4.metric("Unallocated", _pct(unallocated_pct))
            st.caption("Rule of thumb: ~50% needs, ~30% wants, ~20% save & invest. Unallocated is normal.")

            st.divider()
            _section("Net Worth")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Net Worth", _money(net_worth))
            c2.metric("Total Liabilities", _money(total_liabilities))


    st.divider()

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

    st.divider()

    # Emergency minimum 
    st.subheader("🆘 Emergency Minimum")
    e1, e2, e3, e4 = st.columns(4, gap="large")
    e1.metric("Monthly", _money(emergency_minimum_monthly))
    e2.metric("3 mo", _money(emergency_minimum_monthly * 3))
    e3.metric("6 mo", _money(emergency_minimum_monthly * 6))
    e4.metric("12 mo", _money(emergency_minimum_monthly * 12))

    with st.expander("What this includes", expanded=False):
        st.write(f"• **Fixed bills**: {_money(fixed_total)}")
        st.write(f"• **Essentials** (groceries, utilities, healthcare): {_money(essential_variable)}")
        st.write(f"• **Minimum debt**: {_money(debt_minimums)}")

    st.divider()

    # ---- Net worth section ----
    st.subheader("Your Net Worth")
    a_col, l_col = st.columns([1, 1], gap="large")

    with a_col:
        _edit_table(
            title="Assets",
            state_key="pf_assets_df",
            editor_key="pf_assets_editor",
            expected_cols=["Asset", "Value", "Notes"],
            numeric_cols=["Value"],
            column_config={"Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f")},
        )

    with l_col:
        _edit_table(
            title="Liabilities",
            state_key="pf_liabilities_df",
            editor_key="pf_liabilities_editor",
            expected_cols=["Liability", "Value", "Notes"],
            numeric_cols=["Value"],
            column_config={"Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f")},
        )

    n1, n2, n3 = st.columns(3, gap="large")
    n1.metric("Total Assets", _money(total_assets))
    n2.metric("Total Liabilities", _money(total_liabilities))
    n3.metric("Net Worth", _money(net_worth))

    st.divider()

    # ---- Debt info ----
    st.subheader("Debt Details")
    st.caption("This doesn’t affect net worth beyond the liability values — it’s here for clarity + payoff planning.")

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
    st.session_state["pf_debt_df"] = _sanitize_editor_df(
        debt_edit,
        expected_cols=["Debt", "Balance", "APR %", "Monthly Payment", "Notes"],
        numeric_cols=["Balance", "APR %", "Monthly Payment"],
    )

    st.markdown("### Debt Summary")
    c1, c2, c3 = st.columns([0.55, 0.85, 1.2], gap="large")

    with c1:
        st.metric("Total Monthly Debt Payments", _money(total_monthly_debt_payments))

    with c2:
        st.caption(
            "**Debt Burden** = % of take-home pay going to minimum debt payments each month. "
            "Rough guide: under ~15% feels light, 15–30% moderate, 30%+ heavy."
        )
        fig_burden, _ = debt_burden_indicator(net_income=net_income, debt_payments=total_monthly_debt_payments)
        st.plotly_chart(fig_burden, width="stretch")

    with c3:
        st.caption(
            "**Payoff Order** ranks debts for where to focus extra payments. "
            "Bars show **balance**, and the label shows **APR**."
        )
        strategy = st.radio(
            "Payoff strategy",
            ["Avalanche (APR)", "Snowball (Balance)"],
            horizontal=True,
            key="pf_debt_strategy",
            help="Avalanche saves more interest. Snowball builds momentum.",
        )
        fig_order = debt_payoff_order_chart(st.session_state["pf_debt_df"], strategy=strategy)
        st.plotly_chart(fig_order, width="stretch")

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
            "investing_manual_retirement": float(employee_retirement),
            "investing_company_match": float(company_match),
            "saving_and_investing_cashflow_total": float(total_saving_and_investing_cashflow),
            "investing_takehome_only": float(investing_cashflow),
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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"personal_finance_snapshot_{timestamp}.json"
        _download_json_button(
            "Download snapshot (JSON)",
            snapshot,
            filename,
        )    
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

    with st.expander("Import a saved snapshot", expanded=False):
        st.caption("Upload a previously downloaded snapshot JSON to restore your dashboard inputs.")

        uploader_key = f"pf_snapshot_uploader_{st.session_state['pf_uploader_nonce']}"
        uploaded = st.file_uploader("Snapshot JSON", type=["json"], key=uploader_key)

        if uploaded is not None:
            try:
                raw = uploaded.getvalue()
                sig = hashlib.sha256(raw).hexdigest()

                snap = json.loads(raw.decode("utf-8"))

                if not isinstance(snap, dict) or "tables" not in snap:
                    st.error("That file doesn't look like a valid dashboard snapshot.")
                else:
                    # prevent re-queueing on every rerun
                    already_applied = (sig == st.session_state.get("pf_last_import_sig", ""))

                    if already_applied:
                        st.info("Snapshot already applied.")
                    else:
                        st.success("Snapshot ready to import.")
                        if st.button("Apply snapshot now", type="primary", width="stretch"):
                            st.session_state["pf_pending_snapshot"] = snap
                            st.session_state["pf_has_pending_import"] = True

                            # mark as applied + reset uploader so it doesn't keep firing
                            st.session_state["pf_last_import_sig"] = sig
                            st.session_state["pf_uploader_nonce"] += 1

                            st.rerun()

            except Exception as e:
                st.error(f"Couldn't read that file: {e}")

    with st.expander("Reset all data", expanded=False):
        st.warning("This clears the tool's saved tables in this session.")
        if st.button("Reset now", type="primary", key="pf_reset_btn", width="stretch"):
            for k in list(st.session_state.keys()):
                if k.startswith("pf_"):
                    del st.session_state[k]
            st.rerun()