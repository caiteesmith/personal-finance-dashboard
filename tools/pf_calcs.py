# =========================================
# file: tools/pf_calcs.py
# =========================================
from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
import streamlit as st
from tools.pf_state import sum_df


def _estimate_debt_payoff(
    balance: float,
    apr_pct: float,
    payment: float,
    max_months: int = 600,
):
    """
    Simple amortization loop to estimate months to payoff + total interest.

    Returns a dict:
      - status: "paid_off" | "no_payment" | "non_amortizing" | "too_long"
      - months: int | None
      - total_interest: float | None
      - monthly_interest: float
      - min_payment_to_amortize: float
      - reason: str | None
    """
    balance = float(balance or 0.0)
    apr_pct = float(apr_pct or 0.0)
    payment = float(payment or 0.0)

    if balance <= 0:
        return {"status": "paid_off", "months": 0, "total_interest": 0.0, "monthly_interest": 0.0,
                "min_payment_to_amortize": 0.0, "reason": None}

    monthly_rate = max(apr_pct, 0.0) / 100.0 / 12.0
    monthly_interest = balance * monthly_rate if monthly_rate > 0 else 0.0

    if payment <= 0:
        return {
            "status": "no_payment",
            "months": None,
            "total_interest": None,
            "monthly_interest": monthly_interest,
            "min_payment_to_amortize": monthly_interest + 1.0 if monthly_rate > 0 else 0.0,
            "reason": "No monthly payment entered.",
        }

    # No interest case: straight division
    if monthly_rate <= 0:
        months = int(math.ceil(balance / payment))
        return {
            "status": "paid_off",
            "months": months,
            "total_interest": 0.0,
            "monthly_interest": 0.0,
            "min_payment_to_amortize": 0.0,
            "reason": None,
        }

    # Payment doesn't cover interest -> balance grows -> no payoff
    if payment <= monthly_interest:
        # a tiny epsilon above interest is the minimum to *start* amortizing
        min_payment = monthly_interest + 1.0
        return {
            "status": "non_amortizing",
            "months": None,
            "total_interest": None,
            "monthly_interest": monthly_interest,
            "min_payment_to_amortize": min_payment,
            "reason": "Payment is less than (or equal to) monthly interest, so the balance will grow.",
        }

    # Amortize until paid or cap
    months = 0
    total_interest = 0.0
    b = balance

    while b > 0 and months < max_months:
        interest = b * monthly_rate
        principal = payment - interest

        # Should not happen now, but keep it safe
        if principal <= 0:
            return {
                "status": "non_amortizing",
                "months": None,
                "total_interest": None,
                "monthly_interest": interest,
                "min_payment_to_amortize": interest + 1.0,
                "reason": "Payment doesn't reduce principal.",
            }

        b -= principal
        total_interest += interest
        months += 1

    if b > 0:
        return {
            "status": "too_long",
            "months": None,
            "total_interest": total_interest,
            "monthly_interest": monthly_interest,
            "min_payment_to_amortize": monthly_interest + 1.0,
            "reason": f"Not paid off within {max_months} months.",
        }

    return {
        "status": "paid_off",
        "months": months,
        "total_interest": total_interest,
        "monthly_interest": monthly_interest,
        "min_payment_to_amortize": monthly_interest + 1.0,
        "reason": None,
    }


def compute_metrics() -> dict:
    income_df = st.session_state["pf_income_df"]
    fixed_df = st.session_state["pf_fixed_df"]
    essential_df = st.session_state["pf_essential_df"]
    nonessential_df = st.session_state["pf_nonessential_df"]
    saving_df = st.session_state["pf_saving_df"]
    investing_df = st.session_state["pf_investing_df"]
    debt_df = st.session_state["pf_debt_df"]
    assets_df = st.session_state["pf_assets_df"]
    liabilities_df = st.session_state["pf_liabilities_df"]

    # -------- Income / deductions --------
    total_income = sum_df(income_df, "Monthly Amount")

    manual_taxes = float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0)
    manual_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
    manual_benefits = float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0)
    manual_other_ssi = float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0)
    employer_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)

    manual_deductions_total = manual_taxes + manual_retirement + manual_benefits + manual_other_ssi
    use_breakdown = bool(st.session_state.get("pf_use_paycheck_breakdown", False))
    net_income = total_income - manual_deductions_total if use_breakdown else total_income

    est_tax = 0.0  # placeholder if you later add tax-rate mode

    # -------- Expenses / saving / investing --------
    fixed_total = sum_df(fixed_df, "Monthly Amount")
    essential_total = sum_df(essential_df, "Monthly Amount")
    nonessential_total = sum_df(nonessential_df, "Monthly Amount")
    expenses_total = fixed_total + essential_total + nonessential_total

    saving_total = sum_df(saving_df, "Monthly Amount")
    investing_total = sum_df(investing_df, "Monthly Amount")

    investing_cashflow = investing_total
    investing_display = investing_total + manual_retirement + employer_match

    total_monthly_debt_payments = sum_df(debt_df, "Monthly Payment")
    total_saving_and_investing_cashflow = saving_total + investing_cashflow

    total_outflow = expenses_total + total_saving_and_investing_cashflow + total_monthly_debt_payments
    remaining = net_income - total_outflow
    has_debt = total_monthly_debt_payments > 0

    # -------- Net worth --------
    total_assets = sum_df(assets_df, "Value")
    total_liabilities = sum_df(liabilities_df, "Value")
    net_worth = total_assets - total_liabilities

    employee_retirement = float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0)
    company_match = float(st.session_state.get("pf_manual_match", 0.0) or 0.0)
    total_retirement_contrib = employee_retirement + company_match

    investing_rate_of_gross = (investing_display / total_income) * 100 if total_income > 0 else None
    investing_rate_of_net = (investing_display / net_income) * 100 if net_income > 0 else None

    # -------- Emergency minimum / 50-30-20-ish split --------
    debt_minimums = total_monthly_debt_payments
    emergency_minimum_monthly = fixed_total + essential_total + debt_minimums

    needs_total = emergency_minimum_monthly
    wants_total = nonessential_total
    save_invest_total = saving_total + investing_cashflow

    needs_pct = wants_pct = save_invest_pct = unallocated_pct = None
    if net_income > 0:
        needs_pct = (needs_total / net_income) * 100
        wants_pct = (wants_total / net_income) * 100
        save_invest_pct = (save_invest_total / net_income) * 100
        unallocated_pct = max(0.0, 100 - (needs_pct + wants_pct + save_invest_pct))

    # -------- Debt payoff stats --------
    total_debt_balance = sum_df(debt_df, "Balance")

    # Weighted APR for overall payoff estimate (only meaningful if all debts amortize)
    weighted_apr = None
    if total_debt_balance > 0:
        num = 0.0
        for _, row in debt_df.iterrows():
            bal = float(row.get("Balance", 0.0) or 0.0)
            apr = float(row.get("APR %", 0.0) or 0.0)
            num += bal * apr
        weighted_apr = num / total_debt_balance if total_debt_balance > 0 else None

    payoff_rows = []
    has_non_amortizing = False

    for _, row in debt_df.iterrows():
        name = str(row.get("Debt", "") or "").strip() or "Debt"
        bal = float(row.get("Balance", 0.0) or 0.0)
        apr = float(row.get("APR %", 0.0) or 0.0)
        pay = float(row.get("Monthly Payment", 0.0) or 0.0)

        est = _estimate_debt_payoff(bal, apr, pay)

        # Keep even "no payment" and "non-amortizing" entries (wake-up call),
        # but ignore blank/zero-balance rows.
        if bal <= 0:
            continue

        status = est["status"]
        if status in ("non_amortizing", "no_payment", "too_long"):
            has_non_amortizing = True

        payoff_date = None
        months = est.get("months")
        if months is not None and months > 0:
            payoff_date = (pd.Timestamp.today().normalize() + pd.DateOffset(months=months)).strftime("%b %Y")
        elif months == 0:
            payoff_date = "Now"

        payoff_rows.append(
            {
                "Debt": name,
                "balance": bal,
                "apr_pct": apr,
                "payment": pay,
                "status": status,
                "reason": est.get("reason"),
                "monthly_interest": float(est.get("monthly_interest", 0.0) or 0.0),
                "min_payment_to_amortize": float(est.get("min_payment_to_amortize", 0.0) or 0.0),
                "months": months,
                "years": (months / 12.0) if months is not None else None,
                "total_interest": est.get("total_interest"),
                "payoff_date": payoff_date,
            }
        )

    # Overall payoff estimate (all debts combined)
    # If any debt is non-amortizing (or no payment), we should NOT claim an overall payoff date.
    overall_months = overall_interest = None
    overall_payoff_date = None

    if (
        not has_non_amortizing
        and total_debt_balance > 0
        and total_monthly_debt_payments > 0
        and weighted_apr is not None
    ):
        overall_est = _estimate_debt_payoff(
            total_debt_balance,
            weighted_apr,
            total_monthly_debt_payments,
        )
        if overall_est["status"] == "paid_off":
            overall_months = overall_est["months"]
            overall_interest = overall_est["total_interest"]
            if overall_months is not None:
                overall_payoff_date = (
                    pd.Timestamp.today().normalize() + pd.DateOffset(months=overall_months)
                ).strftime("%b %Y")

    # Debt burden (% of net income)
    debt_burden_pct = None
    if net_income > 0 and total_monthly_debt_payments > 0:
        debt_burden_pct = (total_monthly_debt_payments / net_income) * 100

    # -------- Variable df for visuals --------
    variable_for_visuals = pd.concat(
        [essential_df.assign(Category="Essential"), nonessential_df.assign(Category="Non-Essential")],
        ignore_index=True,
        sort=False,
    )

    return {
        "income_df": income_df,
        "fixed_df": fixed_df,
        "essential_df": essential_df,
        "nonessential_df": nonessential_df,
        "saving_df": saving_df,
        "investing_df": investing_df,
        "debt_df": debt_df,
        "assets_df": assets_df,
        "liabilities_df": liabilities_df,

        "total_income": total_income,
        "net_income": net_income,
        "manual_deductions_total": manual_deductions_total,
        "est_tax": est_tax,

        "fixed_total": fixed_total,
        "essential_total": essential_total,
        "nonessential_total": nonessential_total,
        "expenses_total": expenses_total,

        "saving_total": saving_total,
        "investing_total": investing_total,
        "investing_cashflow": investing_cashflow,
        "investing_display": investing_display,

        "total_monthly_debt_payments": total_monthly_debt_payments,
        "total_outflow": total_outflow,
        "remaining": remaining,
        "has_debt": has_debt,

        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,

        "employee_retirement": employee_retirement,
        "company_match": company_match,
        "total_retirement_contrib": total_retirement_contrib,
        "investing_rate_of_gross": investing_rate_of_gross,
        "investing_rate_of_net": investing_rate_of_net,

        "debt_minimums": debt_minimums,
        "emergency_minimum_monthly": emergency_minimum_monthly,

        "needs_pct": needs_pct,
        "wants_pct": wants_pct,
        "save_invest_pct": save_invest_pct,
        "unallocated_pct": unallocated_pct,

        "variable_for_visuals": variable_for_visuals,

        "total_debt_balance": total_debt_balance,
        "debt_weighted_apr": weighted_apr,
        "debt_payoff_rows": payoff_rows,
        "debt_has_non_amortizing": has_non_amortizing,
        "debt_overall_months": overall_months,
        "debt_overall_interest": overall_interest,
        "debt_overall_payoff_date": overall_payoff_date,
        "debt_burden_pct": debt_burden_pct,
    }