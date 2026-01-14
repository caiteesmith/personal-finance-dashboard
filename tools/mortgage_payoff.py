# =========================================
# file: tools/mortgage_payoff.py
# =========================================
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# -------------------------
# Helpers
# -------------------------
def _money(x: float) -> str:
    return f"${float(x or 0.0):,.2f}"


def _to_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def _add_months(d: date, months: int) -> date:
    # Safe month-add without extra deps
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        return 29 if leap else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def _monthly_payment(principal: float, apr_pct: float, term_years: int) -> float:
    """
    Standard amortization payment for fixed-rate mortgage.
    """
    p = float(principal)
    if p <= 0:
        return 0.0

    r = float(apr_pct) / 100.0 / 12.0
    n = int(term_years * 12)

    if n <= 0:
        return 0.0

    if r <= 0:
        return p / n

    pow_ = (1.0 + r) ** n
    return p * r * pow_ / (pow_ - 1.0)


@dataclass
class MortgageResult:
    schedule: pd.DataFrame
    payoff_date: Optional[date]
    months: int
    total_interest: float
    total_paid: float


def build_amortization_schedule(
    *,
    principal: float,
    apr_pct: float,
    monthly_payment: float,
    start_date: date,
    extra_monthly: float = 0.0,
    extra_one_time: float = 0.0,
    extra_one_time_month_index: int = 0,
    max_months: int = 1200,
) -> MortgageResult:
    """
    Builds an amortization schedule until payoff or max_months.
    extra_one_time_month_index: 0-based index (0 = first payment month)
    """
    bal = float(principal)
    apr = float(apr_pct)
    pay = float(monthly_payment)
    extra_m = max(0.0, float(extra_monthly))
    one_time = max(0.0, float(extra_one_time))

    if bal <= 0:
        df = pd.DataFrame(
            columns=[
                "Payment #",
                "Date",
                "Beginning Balance",
                "Payment",
                "Extra",
                "Interest",
                "Principal",
                "Ending Balance",
                "Cumulative Interest",
            ]
        )
        return MortgageResult(df, None, 0, 0.0, 0.0)

    r = apr / 100.0 / 12.0
    EPS = 0.01  # 1 cent payoff tolerance
    if pay <= 0:
        raise ValueError("Monthly payment must be greater than $0.")

    rows = []
    cum_interest = 0.0

    first_interest = bal * r
    if r > 0 and pay <= first_interest:
        raise ValueError(
            "Your monthly payment is not enough to cover monthly interest. "
            "Increase the payment (or check the APR/principal)."
        )

    payoff_dt: Optional[date] = None

    for i in range(max_months):
        if bal <= 0:
            break

        dt = _add_months(start_date, i)
        # Round beginning balance to cents (typical statement style)
        beg = round(beg, 2)

        # Interest is rounded to cents each month in most schedules
        interest = round(beg * r, 2) if r > 0 else 0.0

        # Total due this month (balance + interest), rounded
        due = round(beg + interest, 2)

        # base payment (cannot exceed amount due)
        base_payment = min(round(pay, 2), due)

        # one-time extra happens in the selected month index
        extra_this_month = extra_m + (one_time if i == int(extra_one_time_month_index) else 0.0)
        extra_this_month = round(extra_this_month, 2)

        # total paid this month cannot exceed amount due
        total_payment = min(round(base_payment + extra_this_month, 2), due)

        # split principal/interest (principal also rounded)
        principal_paid = round(max(0.0, total_payment - interest), 2)

        end = round(max(0.0, beg - principal_paid), 2)

        # If we're within a penny, call it paid off
        if end <= EPS:
            principal_paid = round(beg, 2)
            total_payment = round(interest + principal_paid, 2)
            end = 0.0

        cum_interest += interest

        rows.append(
            {
                "Payment #": i + 1,
                "Date": dt,
                "Beginning Balance": beg,
                "Payment": base_payment,
                "Extra": max(0.0, total_payment - base_payment),
                "Interest": interest,
                "Principal": principal_paid,
                "Ending Balance": end,
                "Cumulative Interest": cum_interest,
            }
        )

        bal = end

        if bal <= EPS and payoff_dt is None:
            payoff_dt = dt

    df = pd.DataFrame(rows)

    total_paid = float(df["Payment"].sum() + df["Extra"].sum()) if not df.empty else 0.0
    total_interest = float(df["Interest"].sum()) if not df.empty else 0.0
    months = int(df.shape[0]) if not df.empty else 0

    return MortgageResult(
        schedule=df,
        payoff_date=payoff_dt,
        months=months,
        total_interest=total_interest,
        total_paid=total_paid,
    )


def _balance_chart(schedule: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if schedule is None or schedule.empty:
        return fig

    fig.add_trace(
        go.Scatter(
            x=schedule["Date"],
            y=schedule["Ending Balance"],
            mode="lines",
            name="Balance",
        )
    )
    fig.update_layout(
        title="Remaining Balance Over Time",
        xaxis_title="Date",
        yaxis_title="Balance",
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
    )
    return fig


def render_mortgage_payoff_calculator():
    st.title("🏡 Mortgage Payoff Calculator")
    st.caption(
        "Estimate payoff date, total interest, and how much faster you can pay down your mortgage with extra payments."
    )

    # Defaults
    st.session_state.setdefault("mtg_start_date", date.today().replace(day=1))
    st.session_state.setdefault("mtg_principal", 422000.0)
    st.session_state.setdefault("mtg_home_value", 0.0)  # NEW: used for PMI drop-off
    st.session_state.setdefault("mtg_apr", 6.625)
    st.session_state.setdefault("mtg_term_years", 30)
    st.session_state.setdefault("mtg_mode", "Calculate my payment (term-based)")
    st.session_state.setdefault("mtg_payment_manual", 3400.0)
    st.session_state.setdefault("mtg_extra_monthly", 0.0)
    st.session_state.setdefault("mtg_extra_one_time", 0.0)
    st.session_state.setdefault("mtg_extra_one_time_month", 0)

    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        with st.container(border=True):
            st.subheader("Your Mortgage")

            start_date = st.date_input("Start date (first payment month)", key="mtg_start_date")
            principal = st.number_input("Loan balance/principal", min_value=0.0, step=1000.0, key="mtg_principal")
            home_value = st.number_input(
                "Home value/Purchase price (for PMI drop-off)",
                min_value=0.0,
                step=5000.0,
                key="mtg_home_value",
                help="Used to estimate when PMI can drop off (80% LTV). Set to 0 to disable PMI drop-off logic.",
            )
            apr = st.number_input("Interest rate (APR %)", min_value=0.0, max_value=30.0, step=0.125, key="mtg_apr")

            st.radio(
                "Payment mode",
                ["Calculate my payment (term-based)", "I know my monthly payment"],
                key="mtg_mode",
                horizontal=True,
            )

            if st.session_state["mtg_mode"] == "Calculate my payment (term-based)":
                term_years = st.number_input("Term (years)", min_value=1, max_value=50, step=1, key="mtg_term_years")
                calc_payment = round(_monthly_payment(principal, apr, int(term_years)), 2)
                st.info(f"Estimated monthly payment (principal + interest): **{_money(calc_payment)}**")
                monthly_payment = calc_payment
            else:
                st.number_input(
                    "Monthly payment (principal + interest)",
                    min_value=0.0,
                    step=50.0,
                    key="mtg_payment_manual",
                )
                monthly_payment = float(st.session_state["mtg_payment_manual"] or 0.0)

            st.divider()
            st.subheader("Monthly housing costs (optional)")

            st.session_state.setdefault("mtg_taxes", 0.0)
            st.session_state.setdefault("mtg_insurance", 0.0)
            st.session_state.setdefault("mtg_pmi", 0.0)
            st.session_state.setdefault("mtg_hoa", 0.0)

            t1, t2 = st.columns(2, gap="medium")

            with t1:
                taxes = st.number_input(
                    "Property taxes",
                    min_value=0.0,
                    step=25.0,
                    key="mtg_taxes",
                )
                insurance = st.number_input(
                    "Home insurance",
                    min_value=0.0,
                    step=25.0,
                    key="mtg_insurance",
                )

            with t2:
                pmi = st.number_input(
                    "PMI",
                    min_value=0.0,
                    step=25.0,
                    key="mtg_pmi",
                    help="We can estimate when PMI drops off if you enter a home value above.",
                )
                hoa = st.number_input(
                    "HOA dues",
                    min_value=0.0,
                    step=25.0,
                    key="mtg_hoa",
                )

            st.divider()
            st.subheader("Extra payments (optional)")

            extra_monthly = st.number_input(
                "Extra monthly (toward principal)",
                min_value=0.0,
                step=50.0,
                key="mtg_extra_monthly",
            )

            c1, c2 = st.columns([1, 1], gap="medium")
            with c1:
                extra_one_time = st.number_input(
                    "One-time extra payment",
                    min_value=0.0,
                    step=100.0,
                    key="mtg_extra_one_time",
                )
            with c2:
                extra_one_time_month = st.number_input(
                    "Apply one-time extra in month # (0 = first month)",
                    min_value=0,
                    step=1,
                    key="mtg_extra_one_time_month",
                    help="0 means the first payment month, 1 means the second payment month, etc.",
                )

    # Run calculation
    with right:
        st.subheader("Results")

        try:
            result = build_amortization_schedule(
                principal=float(principal),
                apr_pct=float(apr),
                monthly_payment=float(monthly_payment),
                start_date=start_date,
                extra_monthly=float(extra_monthly),
                extra_one_time=float(extra_one_time),
                extra_one_time_month_index=int(extra_one_time_month),
                max_months=2000,  # generous safety cap
            )
        except ValueError as e:
            st.error(str(e))
            st.stop()

        payoff_date = result.payoff_date
        months = result.months

        taxes_v = float(st.session_state.get("mtg_taxes", 0.0) or 0.0)
        insurance_v = float(st.session_state.get("mtg_insurance", 0.0) or 0.0)
        pmi_v = float(st.session_state.get("mtg_pmi", 0.0) or 0.0)
        hoa_v = float(st.session_state.get("mtg_hoa", 0.0) or 0.0)

        # ---- PMI drop-off detection (80% LTV) ----
        pmi_drop_date: Optional[date] = None
        pmi_drop_month_index: Optional[int] = None

        if float(home_value or 0.0) > 0 and pmi_v > 0 and not result.schedule.empty:
            threshold_balance = float(home_value) * 0.80
            for _, row in result.schedule.iterrows():
                if float(row["Ending Balance"]) <= threshold_balance:
                    pmi_drop_month_index = int(row["Payment #"]) - 1  # 0-based
                    pmi_drop_date = row["Date"]
                    break

        # ---- Monthly housing cost: before/after PMI ----
        non_pi_before = taxes_v + insurance_v + pmi_v + hoa_v
        non_pi_after = taxes_v + insurance_v + hoa_v

        total_housing_before = float(monthly_payment) + non_pi_before
        total_housing_after = float(monthly_payment) + non_pi_after

        # Summary metrics (2x2 grid so values don't truncate)
        r1c1, r1c2 = st.columns(2, gap="large")
        r2c1, r2c2 = st.columns(2, gap="large")

        r1c1.metric("Mortgage P&I", _money(monthly_payment))
        r1c2.metric("Housing (w/ PMI)", _money(total_housing_before))

        r2c1.metric("Payoff (months)", f"{months:,}")
        r2c2.metric("Total Interest Paid", _money(result.total_interest))

        # PMI drop message + updated housing cost after PMI
        if pmi_drop_date:
            st.success(
                f"PMI drops off in **{pmi_drop_date.strftime('%B %Y')}**, "
                f"reducing your monthly housing by **{_money(pmi_v)}**."
            )
            st.caption(f"Monthly housing after PMI: **{_money(total_housing_after)}**")
        elif pmi_v > 0 and float(home_value or 0.0) <= 0:
            st.info("Enter a home value above to estimate when PMI drops off (80% LTV).")

        with st.expander("Monthly housing cost breakdown", expanded=False):
            st.write(f"• **Principal & Interest**: {_money(monthly_payment)}")
            if taxes_v:
                st.write(f"• **Property Taxes**: {_money(taxes_v)}")
            if insurance_v:
                st.write(f"• **Insurance**: {_money(insurance_v)}")

            if pmi_v:
                if pmi_drop_date:
                    st.write(f"• **PMI (until {pmi_drop_date.strftime('%B %Y')})**: {_money(pmi_v)}")
                else:
                    st.write(f"• **PMI**: {_money(pmi_v)}")

            if hoa_v:
                st.write(f"• **HOA**: {_money(hoa_v)}")

        if payoff_date:
            st.success(f"Estimated payoff date: **{payoff_date.strftime('%B %Y')}**")

        st.plotly_chart(_balance_chart(result.schedule), width="stretch")

        with st.expander("View amortization schedule", expanded=False):
            st.dataframe(
                result.schedule.assign(
                    **{
                        "Beginning Balance": result.schedule["Beginning Balance"].map(lambda x: _money(x)),
                        "Payment": result.schedule["Payment"].map(lambda x: _money(x)),
                        "Extra": result.schedule["Extra"].map(lambda x: _money(x)),
                        "Interest": result.schedule["Interest"].map(lambda x: _money(x)),
                        "Principal": result.schedule["Principal"].map(lambda x: _money(x)),
                        "Ending Balance": result.schedule["Ending Balance"].map(lambda x: _money(x)),
                        "Cumulative Interest": result.schedule["Cumulative Interest"].map(lambda x: _money(x)),
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        # Export
        st.divider()
        st.subheader("Export")

        csv_bytes = result.schedule.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download schedule (CSV)",
            data=csv_bytes,
            file_name="mortgage_amortization_schedule.csv",
            mime="text/csv",
            width="stretch",
        )