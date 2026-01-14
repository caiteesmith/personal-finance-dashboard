# tools/pf_visuals.py
from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# CASHFLOW BREAKDOWN BAR CHART
def cashflow_breakdown_chart(
    *,
    net_income: float,
    living_expenses: float,
    debt_payments: float,
    saving: float,
    investing_cashflow: float,
):
    """
    Single stacked bar showing where monthly income goes.
    - If spending exceeds income, shows 'Over budget' instead of negative remainder.
    """
    net_income = float(net_income or 0.0)
    living_expenses = max(float(living_expenses or 0.0), 0.0)
    debt_payments = max(float(debt_payments or 0.0), 0.0)
    saving = max(float(saving or 0.0), 0.0)
    investing_cashflow = max(float(investing_cashflow or 0.0), 0.0)

    total_outflow = living_expenses + debt_payments + saving + investing_cashflow
    remaining = net_income - total_outflow

    remainder_value = max(remaining, 0.0)
    over_budget_value = max(-remaining, 0.0)

    labels = ["Living expenses", "Debt payments", "Saving", "Investing", "Remaining"]
    values = [living_expenses, debt_payments, saving, investing_cashflow, remainder_value]

    if over_budget_value > 0:
        labels.append("Over budget")
        values.append(over_budget_value)

    fig = go.Figure()
    for label, val in zip(labels, values):
        fig.add_trace(
            go.Bar(
                name=label,
                y=[""],
                x=[val],
                orientation="h",
                hovertemplate=f"{label}: $%{{x:,.0f}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=110,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="left", x=0),
        xaxis=dict(title="", tickprefix="$", separatethousands=True),
        yaxis=dict(title="", showticklabels=False),
    )

    return fig, total_outflow, remaining

# SPENDING MIX DONUT CHART
def spending_mix_donut(expenses: float, debt: float, saving: float, investing: float, remaining: float):
    labels, values = [], []

    for label, val in [
        ("Living expenses", expenses),
        ("Debt payments", debt),
        ("Saving", saving),
        ("Investing", investing),
    ]:
        if val > 0:
            labels.append(label)
            values.append(val)

    if remaining > 0:
        labels.append("Remaining")
        values.append(remaining)

    fig = go.Figure(
        data=[go.Pie(labels=labels, values=values, hole=0.55,
                     hovertemplate="%{label}: $%{value:,.0f}<extra></extra>")]
    )

    fig.update_layout(
        title=dict(text="Monthly Cash Flow Breakdown", x=0, xanchor="left", font=dict(size=16)),
        height=280,
        margin=dict(t=50, b=20, l=20, r=20),
        showlegend=True,
    )
    return fig

# TOP EXPENSES BAR CHART
def top_expenses_bar(fixed_df: pd.DataFrame, variable_df: pd.DataFrame):
    df = pd.concat(
        [fixed_df[["Expense", "Monthly Amount"]], variable_df[["Expense", "Monthly Amount"]]],
        ignore_index=True,
    )

    df = (
        df.groupby("Expense", as_index=False)["Monthly Amount"]
        .sum()
        .sort_values("Monthly Amount", ascending=False)
        .head(8)
    )

    fig = go.Figure(
        go.Bar(
            x=df["Monthly Amount"],
            y=df["Expense"],
            orientation="h",
            hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="Top Monthly Expenses", x=0, xanchor="left", font=dict(size=16)),
        height=300,
        margin=dict(l=120, r=20, t=50, b=20),
        xaxis=dict(tickprefix="$", separatethousands=True),
        yaxis=dict(autorange="reversed"),
    )
    return fig

# DEBT PAYMENTS VS BALANCES BAR CHART
def debt_payments_vs_balances(debt_df: pd.DataFrame):
    df = debt_df.copy()

    needed = {"Debt", "Balance", "Monthly Payment"}
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.warning(f"Debt chart skipped: missing columns {missing}")
        return go.Figure()

    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
    df["Monthly Payment"] = pd.to_numeric(df["Monthly Payment"], errors="coerce").fillna(0.0)
    df = df[(df["Balance"] > 0) | (df["Monthly Payment"] > 0)]

    fig = go.Figure()

    fig.add_bar(
        x=df["Debt"],
        y=df["Monthly Payment"],
        name="Monthly Payment",
        hovertemplate="%{x}<br>Payment: $%{y:,.0f}<extra></extra>",
    )

    fig.add_bar(
        x=df["Debt"],
        y=df["Balance"],
        name="Balance",
        hovertemplate="%{x}<br>Balance: $%{y:,.0f}<extra></extra>",
    )

    fig.update_layout(
        title=dict(text="Debt Payments vs. Outstanding Balances", x=0, xanchor="left", font=dict(size=16)),
        barmode="group",
        height=300,
        margin=dict(l=20, r=20, t=50, b=40),
        yaxis=dict(tickprefix="$", separatethousands=True),
    )
    return fig


def render_visual_overview(
    *,
    expenses_total: float,
    total_monthly_debt_payments: float,
    saving_total: float,
    investing_cashflow: float,
    remaining: float,
    fixed_df: pd.DataFrame,
    variable_df: pd.DataFrame,
    debt_df: pd.DataFrame,
):
    st.subheader("Visual Overview")

    v1, v2 = st.columns(2, gap="large")

    with v1:
        st.plotly_chart(
            spending_mix_donut(
                expenses_total,
                total_monthly_debt_payments,
                saving_total,
                investing_cashflow,
                remaining,
            ),
            width="stretch",
        )

    with v2:
        st.plotly_chart(
            debt_payments_vs_balances(debt_df),
            width="stretch",
        )

    st.plotly_chart(
        top_expenses_bar(fixed_df, variable_df),
        width="stretch",
    )