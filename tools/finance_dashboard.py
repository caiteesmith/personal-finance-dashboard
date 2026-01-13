# =========================================
# file: tools/personal_finance_dashboard.py
# =========================================
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
import re

# -------------------------
# Helpers
# -------------------------
def _to_num(x) -> float:
    if x is None or x == "":
        return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _pct(x: float) -> str:
    return f"{x:.1f}%"


def _sum_df(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _ensure_df(key: str, default_rows: List[Dict]) -> pd.DataFrame:
    if key not in st.session_state or not isinstance(st.session_state[key], pd.DataFrame):
        st.session_state[key] = pd.DataFrame(default_rows)
    return st.session_state[key]


def _download_json_button(label: str, payload: Dict, filename: str):
    s = pd.Series(payload).to_json(indent=2)
    st.download_button(label, data=s, file_name=filename, mime="application/json", use_container_width=True)


def _download_csv_button(label: str, df: pd.DataFrame, filename: str):
    st.download_button(label, data=df.to_csv(index=False), file_name=filename, mime="text/csv", use_container_width=True)

def _weekly_from_monthly(monthly: float) -> float:
    return monthly / 4.33

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

# -------------------------
# Defaults
# -------------------------
DEFAULT_INCOME = [
    {"Source": "Paycheck (Net)", "Monthly Amount": 0.0, "Notes": ""}
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
    {"Expense": "TP Fund", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Pet Expenses", "Monthly Amount": 0.0, "Notes": ""},
    {"Expense": "Other", "Monthly Amount": 0.0, "Notes": ""},
]
DEFAULT_SAVING = [
    {"Bucket": "Retirement", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Brokerage", "Monthly Amount": 0.0, "Notes": ""},
    {"Bucket": "Emergency fund", "Monthly Amount": 0.0, "Notes": ""},
]
DEFAULT_DEBT = [
    {"Debt": "Credit card", "Balance": 0.0, "APR %": 0.0, "Monthly Payment": 0.0, "Notes": ""},
]
DEFAULT_ASSETS = [
    {"Asset": "Checking", "Value": 0.0, "Notes": ""},
    {"Asset": "Savings", "Value": 0.0, "Notes": ""},
    {"Asset": "Brokerage", "Value": 0.0, "Notes": ""},
    {"Asset": "Retirement", "Value": 0.0, "Notes": ""},
    {"Asset": "Value of Home (minus debt)", "Value": 0.0, "Notes": ""},
    {"Asset": "Value of Vehicle (minus debt)", "Value": 0.0, "Notes": ""}
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
        "Enter your numbers, and the tool does the math."
    )

    # ---- Global settings ----
    with st.expander("Settings", expanded=False):
        c1, c2, c3 = st.columns([1, 1, 1], gap="large")
        with c1:
            month_label = st.text_input("Month label", value=datetime.now().strftime("%B %Y"), key="pf_month_label")
        with c2:
            tax_rate = st.number_input(
                "Estimated effective tax rate (%)",
                min_value=0.0,
                max_value=60.0,
                value=float(st.session_state.get("pf_tax_rate", 0.0) or 0.0),
                step=0.5,
                key="pf_tax_rate",
                help="Optional. If you enter *gross* income, this helps estimate post-tax cash flow.",
            )
        with c3:
            income_is = st.selectbox(
                "Income amounts are…",
                ["Net (after tax)", "Gross (before tax)"],
                index=0,
                key="pf_income_is",
            )

    # ---- Tables ----
    if "pf_income_df" not in st.session_state:
        st.session_state["pf_income_df"] = pd.DataFrame(DEFAULT_INCOME)

    income_df = st.session_state["pf_income_df"]

    if "pf_fixed_df" not in st.session_state:
        st.session_state["pf_fixed_df"] = pd.DataFrame(DEFAULT_FIXED)

    fixed_df = st.session_state["pf_fixed_df"]

    if "pf_variable_df" not in st.session_state:
        st.session_state["pf_variable_df"] = pd.DataFrame(DEFAULT_VARIABLE)

    variable_df = st.session_state["pf_variable_df"]

    if "pf_saving_df" not in st.session_state:
        st.session_state["pf_saving_df"] = pd.DataFrame(DEFAULT_SAVING)

    saving_df = st.session_state["pf_saving_df"]

    if "pf_debt_df" not in st.session_state:
        st.session_state["pf_debt_df"] = pd.DataFrame(DEFAULT_DEBT)

    debt_df = st.session_state["pf_debt_df"]

    if "pf_assets_df" not in st.session_state:
        st.session_state["pf_assets_df"] = pd.DataFrame(DEFAULT_ASSETS)

    assets_df = st.session_state["pf_assets_df"]

    if "pf_liabilities_df" not in st.session_state:
        st.session_state["pf_liabilities_df"] = pd.DataFrame(DEFAULT_LIABILITIES)

    liabilities_df = st.session_state["pf_liabilities_df"]

    st.subheader("Monthly Cash Flow")

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        tab_income, tab_exp, tab_save = st.tabs(["Income", "Expenses", "Saving / Investing"])

        with tab_income:
            st.write("Add your income sources (monthly amounts).")
            income_df = st.data_editor(
                income_df,
                num_rows="dynamic",
                use_container_width=True,
                key="pf_income_editor",
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.2f"),
                },
            )
            st.session_state["pf_income_df"] = income_df

        with tab_exp:
            st.write("Split your expenses into fixed & variable so you can see what's flexible.")
            st.markdown("**Fixed Expenses**")
            fixed_df = st.data_editor(
                fixed_df,
                num_rows="dynamic",
                use_container_width=True,
                key="pf_fixed_editor",
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                },
            )
            st.session_state["pf_fixed_df"] = fixed_df

            st.markdown("**Variable Expenses**")
            variable_df = st.data_editor(
                variable_df,
                num_rows="dynamic",
                use_container_width=True,
                key="pf_variable_editor",
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                },
            )
            st.session_state["pf_variable_df"] = variable_df

        with tab_save:
            st.write("Monthly contributions you want to make (Retirement, brokerage, emergency fund, etc.).")
            saving_df = st.data_editor(
                saving_df,
                num_rows="dynamic",
                use_container_width=True,
                key="pf_saving_editor",
                column_config={
                    "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f"),
                },
            )
            st.session_state["pf_saving_df"] = saving_df

    # ---- Calculate monthly cash flow ----
    total_income = _sum_df(income_df, "Monthly Amount")
    est_tax = 0.0
    if income_is == "Gross (before tax)" and tax_rate > 0:
        est_tax = total_income * (tax_rate / 100.0)
        net_income = total_income - est_tax
    else:
        net_income = total_income

    fixed_total = _sum_df(fixed_df, "Monthly Amount")
    variable_total = _sum_df(variable_df, "Monthly Amount")
    expenses_total = fixed_total + variable_total

    saving_total = _sum_df(saving_df, "Monthly Amount")

    remaining = net_income - expenses_total - saving_total

    # ---- Emergency Minimum (assumption-based) ----
    # All fixed expenses + essential variable categories + debt minimum payments
    ESSENTIAL_VARIABLE_KEYWORDS = [
        # groceries / food at home
        "grocery", "groceries",

        # utilities
        "electric", "electricity", "gas", "water", "sewer", "trash", "garbage",
        "utility", "utilities",

        # comms
        "internet", "wifi", "phone", "cell",

        # insurance + health (common essentials)
        "insurance", "medical", "health", "prescription", "rx",

        # transportation essentials
        "gasoline", "fuel", "transit", "train", "toll", "parking",
    ]

    essential_variable = _sum_by_keywords(
        variable_df,
        name_col="Expense",
        amount_col="Monthly Amount",
        keywords=ESSENTIAL_VARIABLE_KEYWORDS,
    )

    debt_minimums = _sum_df(debt_df, "Monthly Payment")

    emergency_minimum_monthly = fixed_total + essential_variable + debt_minimums

    with right:
        # --- Summary Card ---
        st.markdown("#### Summary")

        st.markdown(
            """
            <div style="
                background: rgba(15, 26, 22, 0.85);
                border: 1px solid rgba(230, 240, 236, 0.14);
                border-radius: 16px;
                padding: 16px 16px 6px 16px;
                margin-top: 8px;
                margin-bottom: 14px;
            ">
            """,
            unsafe_allow_html=True,
        )

        # Top row (most important)
        s1, s2 = st.columns([1, 1], gap="medium")
        with s1:
            st.metric(
                "Net Income (monthly)",
                _money(net_income),
                help="If you selected gross income, this is estimated after tax.",
            )
            if income_is == "Gross (before tax)" and tax_rate > 0:
                st.metric("Estimated Taxes (monthly)", _money(est_tax))

        with s2:
            st.metric("Left Over (monthly)", _money(remaining))

        # Second row (supporting totals)
        s3, s4 = st.columns([1, 1], gap="medium")
        with s3:
            st.metric("Total Expenses (monthly)", _money(expenses_total))
        with s4:
            st.metric("Saving / Investing (monthly)", _money(saving_total))

        # Safe-to-spend (still useful, but visually secondary)
        safe_weekly = remaining / 4.33
        safe_daily = remaining / 30.4

        s5, s6 = st.columns([1, 1], gap="medium")
        with s5:
            st.metric(
                "Safe-to-spend (weekly)",
                _money(safe_weekly),
                help="Left over divided by ~4.33 weeks per month.",
            )
        with s6:
            st.metric(
                "Safe-to-spend (daily)",
                _money(safe_daily),
                help="Left over divided by ~30.4 days per month.",
            )

        # Status messaging
        if remaining < 0:
            st.error("You’re budgeting more than you’re bringing in this month.")
        elif remaining < 200:
            st.warning("This month is very tight — you don’t have much buffer.")
        else:
            st.success("You’ve got some breathing room this month.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🆘 Emergency Minimum (Assumption-Based)")
    st.caption(
        "Estimated minimum monthly amount needed if income stops: "
        "Fixed expenses + utilities/groceries + debt minimum payments (auto-detected by name)."
    )

    e1, e2, e3, e4 = st.columns(4, gap="large")
    e1.metric("Emergency Minimum (monthly)", _money(emergency_minimum_monthly))
    e2.metric("3 months", _money(emergency_minimum_monthly * 3))
    e3.metric("6 months", _money(emergency_minimum_monthly * 6))
    e4.metric("12 months", _money(emergency_minimum_monthly * 12))

    st.write("Your emergency minimum covers:")
    st.write(
        f"• **Fixed bills** (housing, insurance, phone): {_money(fixed_total)}"
    )
    st.write(
        f"• **Essentials** (groceries, utilities, transportation): {_money(essential_variable)}"
    )
    st.write(
        f"• **Debt payments** you must make: {_money(debt_minimums)}"
    )

    st.divider()

    # ---- Net worth section ----
    st.subheader("Net Worth")

    a_col, l_col = st.columns([1, 1], gap="large")

    with a_col:
        st.markdown("**Assets**")
        assets_df = st.data_editor(
            assets_df,
            num_rows="dynamic",
            use_container_width=True,
            key="pf_assets_editor",
            column_config={
                "Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
            },
        )
        st.session_state["pf_assets_df"] = assets_df

    with l_col:
        st.markdown("**Liabilities**")
        liabilities_df = st.data_editor(
            liabilities_df,
            num_rows="dynamic",
            use_container_width=True,
            key="pf_liabilities_editor",
            column_config={
                "Value": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
            },
        )
        st.session_state["pf_liabilities_df"] = liabilities_df

    total_assets = _sum_df(assets_df, "Value")
    total_liabilities = _sum_df(liabilities_df, "Value")
    net_worth = total_assets - total_liabilities

    n1, n2, n3 = st.columns(3, gap="large")
    n1.metric("Total Assets", _money(total_assets))
    n2.metric("Total Liabilities", _money(total_liabilities))
    n3.metric("Net Worth", _money(net_worth))

    st.divider()

    # ---- Debt info (optional, extra nerdy) ----
    st.subheader("Debt Details (optional)")
    st.caption("This doesn't affect net worth beyond the liability values — it's here for clarity and planning.")

    debt_df = st.data_editor(
        debt_df,
        num_rows="dynamic",
        use_container_width=True,
        key="pf_debt_editor",
        column_config={
            "Balance": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%.2f"),
            "APR %": st.column_config.NumberColumn(min_value=0.0, max_value=60.0, step=0.1, format="%.2f"),
            "Monthly Payment": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
        },
    )
    st.session_state["pf_debt_df"] = debt_df

    total_debt_payment = _sum_df(debt_df, "Monthly Payment")
    st.metric("Total Monthly Debt Payments", _money(total_debt_payment))

    st.divider()

    # ---- Exports + snapshot ----
    st.subheader("Export / Save Snapshot")

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "month_label": month_label,
        "settings": {
            "income_is": income_is,
            "tax_rate_pct": float(tax_rate),
        },
        "monthly_cash_flow": {
            "total_income_entered": float(total_income),
            "estimated_taxes": float(est_tax),
            "net_income": float(net_income),
            "fixed_expenses": float(fixed_total),
            "variable_expenses": float(variable_total),
            "total_expenses": float(expenses_total),
            "saving_investing": float(saving_total),
            "left_over": float(remaining),
            "safe_to_spend_weekly": float(safe_weekly),
            "safe_to_spend_daily": float(safe_daily),
        },
        "net_worth": {
            "assets_total": float(total_assets),
            "liabilities_total": float(total_liabilities),
            "net_worth": float(net_worth),
        },
        "tables": {
            "income": income_df.to_dict(orient="records"),
            "fixed_expenses": fixed_df.to_dict(orient="records"),
            "variable_expenses": variable_df.to_dict(orient="records"),
            "saving": saving_df.to_dict(orient="records"),
            "assets": assets_df.to_dict(orient="records"),
            "liabilities": liabilities_df.to_dict(orient="records"),
            "debt_details": debt_df.to_dict(orient="records"),
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
                income_df.assign(Table="Income"),
                fixed_df.assign(Table="Fixed Expenses"),
                variable_df.assign(Table="Variable Expenses"),
                saving_df.assign(Table="Saving/Investing"),
            ],
            ignore_index=True,
            sort=False,
        )
        _download_csv_button("Download monthly tables (CSV)", combined, "personal_finance_monthly_tables.csv")
    with cC:
        nw_combined = pd.concat(
            [
                assets_df.rename(columns={"Asset": "Item"}).assign(Type="Asset"),
                liabilities_df.rename(columns={"Liability": "Item"}).assign(Type="Liability"),
            ],
            ignore_index=True,
            sort=False,
        )
        _download_csv_button("Download net worth tables (CSV)", nw_combined, "personal_finance_net_worth_tables.csv")

    with st.expander("Reset all data", expanded=False):
        st.warning("This clears the tool’s saved tables in this session.")
        if st.button("Reset now", type="primary", key="pf_reset_btn"):
            for k in [
                "pf_income_df",
                "pf_fixed_df",
                "pf_variable_df",
                "pf_saving_df",
                "pf_debt_df",
                "pf_assets_df",
                "pf_liabilities_df",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()