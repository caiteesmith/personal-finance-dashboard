# =========================================
# file: tools/finance_dashboard.py
# =========================================
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
import re
import streamlit as st

from tools.pf_visuals import cashflow_breakdown_chart, render_visual_overview, debt_burden_indicator, debt_payoff_order_chart

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
    {"Expense": "Gym/Fitness", "Monthly Amount": 0.0, "Notes": ""},
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
        "A spreadsheet-style dashboard to track your personal monthly cash flow and net worth. "
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
    with st.expander("Income Settings & Tax/Deduction Options", expanded=False):
        st.caption(
            "Choose whether your income is entered as net or gross. "
            "If you enter gross income, you can estimate taxes or define exact monthly deductions below."
        )
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

        # ---- Gross Breakdown ----
        if income_is == "Gross (before tax)":
            st.subheader("Gross Income Breakdown (monthly)")
            st.caption(
                "Use this section only if you want to enter your income as gross, e.g. a paycheck breakdown. "
                "You can estimate taxes or enter exact monthly deductions for more accurate cash flow."
            )
            st.radio(
                "How should we calculate net income?",
                ["Estimate (tax rate)", "Manual deductions"],
                key="pf_gross_mode",
                horizontal=True,
            )

            with st.form("pf_gross_breakdown_form", border=False):
                manual_mode = st.session_state.get("pf_gross_mode") == "Manual deductions"

                g1, g2, g3 = st.columns(3, gap="large")
                with g1:
                    st.number_input("Taxes", min_value=0.0, step=50.0, key="pf_manual_taxes", disabled=not manual_mode)
                    st.number_input("Benefits", min_value=0.0, step=25.0, key="pf_manual_benefits", disabled=not manual_mode)

                with g2:
                    st.number_input("Retirement (employee)", min_value=0.0, step=50.0, key="pf_manual_retirement", disabled=not manual_mode)
                    st.number_input("Other/SSI", min_value=0.0, step=25.0, key="pf_manual_other_ssi", disabled=not manual_mode)

                with g3:
                    st.number_input(
                        "Company Match (optional)",
                        min_value=0.0,
                        step=50.0,
                        key="pf_manual_match",
                        help="Tracked as extra retirement contribution; does not reduce take-home.",
                        disabled=not manual_mode,
                    )

                submitted = st.form_submit_button("Save gross breakdown", width="stretch", disabled=not manual_mode)

                if submitted:
                    st.success("Saved.")
                    st.rerun()

            if st.session_state.get("pf_gross_mode") != "Manual deductions":
                st.info("Using estimated tax rate. Switch to Manual deductions if you want to specify exact amounts.")

    # -------------------------
    # EDITORS
    # -------------------------
    st.subheader("Your Monthly Cash Flow")
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        tab_income, tab_exp, tab_save = st.tabs(["Income", "Expenses", "Saving/Investing"])

        with tab_income:
            st.write(
                "Add your income sources. If you have a two-income household, include both here."
            )
            st.caption(
                "For paycheck-level accuracy (pre-tax 401k contributions, employer match, benefits, and taxes), "
                "use the Income Settings & Tax/Deduction Options section above."
            )

            with tab_exp:
                st.write("Split your expenses into fixed & variable so you can see what's flexible.")

                with st.expander("Quick reality check to help your numbers be accurate", expanded=False):
                    st.caption(
                        "This dashboard is only as good as the inputs. Before you guess, take 5-10 minutes to be brutally honest "
                        "and scan the last 1-2 months of statements."
                    )

                    st.markdown(
                        """
                            **Where to look**
                            - Bank & credit card statements: Search for common merchants (Starbucks, Dunkin, Wawa, etc.)
                            - Amazon: Check Subscribe & Save and recurring orders
                            - Apple/Google subscriptions: iCloud / Google Drive storage, app subscriptions
                            - Spotify/Netflix/HBO Max/Hulu/Paramount Plus/Peacock/YouTube Premium
                            - Gym memberships, class packs, and any “trial turned paid”
                            - Vitamins/supplements, skincare, contact supplies
                            - Coffee runs, snacks, “little treats” (they add up fast)
                        """
                    )
                    st.info("Tip: If something hits monthly (or “randomly but often”), it belongs here.")
                    st.checkbox("I checked statements & subscriptions before filling this out", key="pf_expenses_reality_check")
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

    investing_cashflow = investing_total
    investing_display = investing_total

    payroll_retirement = 0.0
    employer_match = 0.0

    if income_is == "Gross (before tax)" and st.session_state.get("pf_gross_mode") == "Manual deductions":
        payroll_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
        employer_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)

        investing_display = investing_total + payroll_retirement + employer_match

        investing_cashflow = investing_total

    manual_retirement = payroll_retirement
    company_match = employer_match

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

    investing_rate_of_gross = None
    investing_rate_of_net = None

    if total_income > 0:
        investing_rate_of_gross = (investing_display / total_income) * 100

    if net_income > 0:
        investing_rate_of_net = (investing_display / net_income) * 100

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
        if not st.session_state.get("pf_expenses_reality_check", False):
            st.info(
                "Quick reminder: Reviewing bank statements and subscriptions "
                "can help make your expense numbers more accurate."
            )

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

        # ---- Summary section ----
        with st.container(border=True):
            _section("Net & Gross Income")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Net Income", _money(net_income))
            c2.metric("Gross Income", _money(total_income))

        st.write("")

        with st.container(border=True):
            _section("Expenses, Debt, Investments, & Savings")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Living Expenses", _money(expenses_total))
            c2.metric("Debt Payments", _money(total_monthly_debt_payments))

            c3, c4 = st.columns(2, gap="medium")
            c3.metric("Saving", _money(saving_total))
            c4.metric("Investing", _money(investing_display))

            c5, c6 = st.columns(2, gap="medium")
            c5.metric("Total Expenses", _money(total_outflow))
            c6.metric(
                "Gross Income Invested",
                _pct(investing_rate_of_gross),
                help="Investing divided by total pre-tax income."
            )
        with st.container(border=True):
            _section("Remaining (After Bills, Saving & Investing)")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Monthly", _money(remaining))
            c2.metric("Weekly", _money(remaining / 4.33))
            c3, _ = st.columns(2, gap="medium")
            c3.metric("Daily", _money(remaining / 30.4))

            with st.expander("What You Can Do With the Remaining", expanded=False):
                st.caption(
                    "This is optional guidance, there's no single right answer. "
                    "Use what fits your goals and current season of life."
                )

                if remaining <= 0:
                    st.info(
                        "You're currently allocating all of your income. "
                        "If things feel tight, consider reducing discretionary expenses or lowering savings temporarily."
                    )
                else:
                    st.markdown(
                        f"**You have {_money(remaining)} available each month.** Here are common, intentional ways people use it:"
                    )

                    bullets = []

                    bullets.append("Build/boost savings: Emergency fund, short-term goals, or sinking funds.")
                    bullets.append("Invest more: Brokerage, retirement, or HSA if you're not maxing them yet.")

                    if has_debt:
                        bullets.append("Pay down debt faster: Extra principal on high-interest debt or your mortgage.")
                    else:
                        bullets.append("Invest toward future goals: Home upgrades, travel, FIRE, or long-term flexibility.")

                    bullets.append("Spend intentionally: Guilt-free fun money that's already accounted for.")
                    bullets.append("Reallocate later: It's okay to wait a month and decide once patterns emerge.")

                    for b in bullets:
                        st.markdown(f"- {b}")

                    st.info(
                        "Tip: If you're unsure, try assigning a default (like 50% invest, 30% enjoy, 20% save) "
                        "and adjust after a few months."
                    )

                    st.markdown("**A common reference: the 50-30-20 budget guideline**")

                    st.markdown(
                        """
                        This is a *rule of thumb*, not a requirement:

                        - **~50% Needs**: Housing, utilities, groceries, insurance, minimum debt payments  
                        - **~30% Wants**: Dining out, subscriptions, travel, fun spending  
                        - **~20% Save & Invest**: Emergency fund, investing, extra debt payments

                        If your numbers don't fit this exactly, that's totally normal, especially with high housing costs, student loans, or aggressive saving goals.
                        """
                    )


        with st.container(border=True):
            _section("Net Worth & Liabilities")
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

    st.markdown("### Debt Summary")
    c1, c2, c3 = st.columns([0.55, 0.85, 1.2], gap="large")

    with c1:
        st.metric(
            "Total Monthly Debt Payments",
            _money(total_monthly_debt_payments),
            help="The total minimum amount you must pay toward debts each month."
        )

    with c2:
        st.caption(
            "**Debt Burden** shows what % of your take-home pay goes to minimum debt payments each month. "
            "Lower is more flexible. Rough guide: under ~15% feels light, 15–30% is moderate, 30%+ is heavy."
        )
        fig_burden, burden_pct = debt_burden_indicator(
            net_income=net_income,
            debt_payments=total_monthly_debt_payments,
        )
        st.plotly_chart(fig_burden, width="stretch")

    with c3:
        st.caption(
            "**Payoff Order** ranks your debts for where to focus extra payments. "
            "Bars show **balance**, and the label on each bar is the **APR**."
        )
        strategy = st.radio(
            "Payoff strategy",
            ["Avalanche (APR)", "Snowball (Balance)"],
            horizontal=True,
            key="pf_debt_strategy",
            help="Avalanche saves more interest (highest APR first). Snowball builds momentum (smallest balance first).",
        )
        fig_order = debt_payoff_order_chart(st.session_state["pf_debt_df"], strategy=strategy)
        st.plotly_chart(fig_order, width="stretch")

    st.caption(
        "Tip: Keep paying minimums on everything, then put any extra toward the #1 ranked debt. "
        "If you have leftover income each month, put as much as possible toward your debt(s)."
    )

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