# =========================================
# file: tools/pf_ui_summary.py
# =========================================
from __future__ import annotations

import streamlit as st

from tools.pf_state import money, pct
from tools.pf_visuals import cashflow_breakdown_chart


def render_summary_panel(metrics: dict) -> None:
    """
    Renders the right-side panel.
    No early return; summary is always available,
    but is collapsed when state is empty.
    """

    def _section(title: str):
        st.markdown(
            f"<div style='font-size:0.85rem; letter-spacing:.06em; text-transform:uppercase; "
            f"opacity:.70; margin: 0.2rem 0 0.6rem 0;'>{title}</div>",
            unsafe_allow_html=True,
        )

    def _is_empty_state() -> bool:
        return (
            (metrics.get("total_income", 0) <= 0)
            and (metrics.get("expenses_total", 0) <= 0)
            and (metrics.get("saving_total", 0) <= 0)
            and (metrics.get("investing_total", 0) <= 0)
            and (metrics.get("total_assets", 0) <= 0)
            and (metrics.get("total_liabilities", 0) <= 0)
            and (metrics.get("total_monthly_debt_payments", 0) <= 0)
        )

    # -------------------------
    # Pull metrics
    # -------------------------
    net_income = float(metrics.get("net_income", 0.0) or 0.0)
    total_income = float(metrics.get("total_income", 0.0) or 0.0)

    expenses_total = float(metrics.get("expenses_total", 0.0) or 0.0)
    debt_payments = float(metrics.get("total_monthly_debt_payments", 0.0) or 0.0)
    saving_total = float(metrics.get("saving_total", 0.0) or 0.0)
    investing_cashflow = float(metrics.get("investing_cashflow", 0.0) or 0.0)
    investing_display = float(metrics.get("investing_display", 0.0) or 0.0)

    total_outflow = float(metrics.get("total_outflow", 0.0) or 0.0)
    remaining = float(metrics.get("remaining", 0.0) or 0.0)

    investing_rate_of_gross = metrics.get("investing_rate_of_gross")
    needs_pct = metrics.get("needs_pct")
    wants_pct = metrics.get("wants_pct")
    save_invest_pct = metrics.get("save_invest_pct")
    unallocated_pct = metrics.get("unallocated_pct")

    net_worth = float(metrics.get("net_worth", 0.0) or 0.0)
    total_assets = float(metrics.get("total_assets", 0.0) or 0.0)
    total_liabilities = float(metrics.get("total_liabilities", 0.0) or 0.0)

    has_debt = bool(metrics.get("has_debt", False))
    use_breakdown = bool(st.session_state.get("pf_use_paycheck_breakdown", False))

    is_empty = _is_empty_state()

    # -------------------------
    # EMPTY STATE WELCOME (above Summary)
    # -------------------------
    if is_empty:
        with st.container(border=True):
            st.markdown("### Welcome 👋")
            st.caption(
                "A spreadsheet-style dashboard to track your personal monthly cash flow and net worth. "
                "Enter your numbers, click Save, and the tool does the math."
            )
            st.markdown(
                """
                **Start here:**
                1. **Income:** Add your real monthly take-home pay (or gross if you're using paycheck breakdown).
                2. **Fixed bills:** Housing, car payment, insurance, phone, internet.
                3. **Essentials:** Groceries, utilities, healthcare, transit, childcare.
                4. **Non-essentials:** Dining out, subscriptions, entertainment, shopping.
                5. **Saving/Investing:** Add what you *actually* contribute per month.
                6. **Debt & Net Worth:** Optional, but it makes the picture way clearer.

                **Tiny tips that keep this accurate**
                - Use real numbers, not guesses. Pull from the last 1-2 months statements so it matches real life.
                - Convert to monthly amounts (ex: annual bill ÷ 12).
                - Click **Save** in each tab to update your snapshot.
                - Want to keep your data? Use **Export snapshot** (then you can import it later).
                """
            )

    # -------------------------
    # SUMMARY
    # -------------------------
    if is_empty:
        summary_box = st.expander("Summary", expanded=False)
    else:
        summary_box = st.container(border=True)

    with summary_box:
        if is_empty:
            st.markdown("### Summary")

            st.caption(
                "Once you add income, expenses, or saving/investing and click **Save** in the tabs, "
                "this panel will fill in with your personalized snapshot."
            )
            return

        # ---------- This Month at a Glance ----------
        st.subheader("This Month at a Glance")
        fig, _, _ = cashflow_breakdown_chart(
            net_income=net_income,
            living_expenses=expenses_total,
            debt_payments=debt_payments,
            saving=saving_total,
            investing_cashflow=investing_cashflow,
        )
        st.plotly_chart(fig, width="stretch")

        # ---------- Net & Gross ----------
        with st.container(border=True):
            if use_breakdown:
                _section("Net & Gross Income")
                c1, c2 = st.columns(2, gap="medium")
                c1.metric("Net Income (after deductions)", money(net_income))
                c2.metric("Gross Income", money(total_income))
                st.caption(
                    "Gross is what you entered under Income. "
                    "Net subtracts the monthly deductions from the paycheck breakdown."
                )
            else:
                _section("Net Income")
                c1, _ = st.columns(2, gap="medium")
                c1.metric("Monthly Income", money(net_income))
                st.caption(
                    "Paycheck breakdown is off, so this is treated as net income. "
                    "If you enter gross pay, turn on paycheck breakdown to calculate net."
                )

        # ---------- Expenses / Debt / Save / Invest ----------
        with st.container(border=True):
            _section("Expenses, Debt, Investments, & Savings")
            c1, c2 = st.columns(2, gap="medium")
            c1.metric("Living Expenses", money(expenses_total))
            c2.metric("Debt Payments", money(debt_payments))

        with st.container(border=True):
            c3, c4 = st.columns(2, gap="medium")
            c3.metric("Saving", money(saving_total))
            c4.metric("Investing", money(investing_display))

        with st.container(border=True):
            c5, c6 = st.columns(2, gap="medium")
            c5.metric("Total Expenses", money(total_outflow))
            c6.metric(
                "Gross Income Invested",
                pct(investing_rate_of_gross),
                help="Investing divided by total pre-tax income.",
            )

        # ---------- Remaining ----------
        with st.container(border=True):
            _section("Remaining (After Expenses, Saving & Investing)")

            safe_weekly = remaining / 4.33
            safe_biweekly = remaining / (4.33 / 2)
            safe_daily = remaining / 30.4

            r1c1, r1c2 = st.columns(2, gap="medium")
            r1c1.metric("Monthly", money(remaining))
            r1c2.metric("Biweekly", money(safe_biweekly))

            r2c1, r2c2 = st.columns(2, gap="medium")
            r2c1.metric("Weekly", money(safe_weekly))
            r2c2.metric("Daily", money(safe_daily))

        # ---------- How you're doing ----------
        with st.expander("How you're doing", expanded=False):
            with st.container(border=True):
                _section("How you're doing")
                buffer = max(remaining, 0.0)

                if remaining < 0:
                    st.error(
                        f"You're over-allocated by **{money(abs(remaining))}** this month. "
                        "No shame, it just means something needs to give (even temporarily)."
                    )
                    st.markdown(
                        "- Trim **non-essentials** first (subscriptions, dining out, random spending)\n"
                        "- Or lower saving/investing for a month while you stabilize\n"
                        "- If debt is heavy, put extra money toward the highest-interest balance"
                    )
                elif buffer < 200:
                    st.warning(
                        f"You've got **{money(buffer)}** left unallocated. "
                        "That's a tight buffer; doable, but stressful when life happens."
                    )
                    st.markdown("If it feels tight, aim for a buffer closer to **\\$200-\\$500**.")
                elif buffer < 700:
                    st.success(f"You've got **{money(buffer)}** left unallocated. That gives you real breathing room.")
                    st.markdown(
                        "Great range for stability & flexibility. You can decide later whether to save it, "
                        "invest it, or use it intentionally."
                    )
                else:
                    st.success(f"You've got **{money(buffer)}** left unallocated. That's a comfortable margin to work with.")
                    st.markdown(
                        "You could:\n"
                        "- Build your emergency fund faster\n"
                        "- Invest more\n"
                        "- Pay down debt faster\n"
                        "- Set aside guilt-free fun money\n"
                        "- Or keep it as buffer while you watch patterns for a few months"
                    )

        # ---------- Split + Net Worth ----------
        with st.container(border=True):
            _section("Spending & Saving Split")
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            c1.metric("Needs", pct(needs_pct), help="Housing + essentials + minimum debt.")
            c2.metric("Wants", pct(wants_pct), help="Non-essential spending (subscriptions, dining, shopping, etc.).")
            c3.metric("Save & Invest", pct(save_invest_pct), help="Savings + investing/retirement contributions.")
            c4.metric("Unallocated", pct(unallocated_pct), help="Not assigned yet (often buffer/flex).")
            st.caption(
                "Rule of thumb: ~50% needs, ~30% wants, ~20% save & invest. "
                "Unallocated is normal and often intentional."
            )

        with st.container(border=True):
            _section("Net Worth & Liabilities")
            c1, c2, c3 = st.columns(3, gap="medium")
            c1.metric("Total Assets", f"${total_assets:,.0f}")
            c2.metric("Total Liabilities", f"${total_liabilities:,.0f}")
            c3.metric("Net Worth", f"${net_worth:,.0f}")