# tools/pf_visuals.py
from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ------------------------------
# CASHFLOW BREAKDOWN BAR CHART
# ------------------------------
def cashflow_breakdown_chart(
    *,
    net_income: float,
    living_expenses: float,
    debt_payments: float,
    saving: float,
    investing_cashflow: float,
):
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

    max_x = max(net_income, total_outflow, 1.0)

    fig = go.Figure()

    for label, val in zip(labels, values):
        fig.add_trace(
            go.Bar(
                name=label,
                y=[0],
                x=[val],
                orientation="h",
                hovertemplate=f"{label}: $%{{x:,.0f}}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=96,
        margin=dict(l=0, r=0, t=6, b=22),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.10,
            xanchor="left",
            x=0,
            font=dict(size=13),
            itemwidth=80,
        ),
        xaxis=dict(
            range=[0, max_x],
            tickprefix="$",
            separatethousands=True,
            showgrid=False,
            zeroline=False,
            fixedrange=True,
            automargin=False,
            ticklabelposition="inside",
            tickpadding=12,
            domain=[0, 1],
        ),
        yaxis=dict(
            range=[-0.5, 0.5],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            fixedrange=True,
            domain=[0, 1],
        ),
    )

    fig.update_traces(marker=dict(line=dict(width=0)))

    return fig, total_outflow, remaining

# ------------------------------
# SPENDING MIX DONUT CHART
# ------------------------------
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

# ------------------------------
# TOP EXPENSES BAR CHART
# ------------------------------
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

# ------------------------------
# DEBT PAYMENTS VS BALANCES BAR CHART
# ------------------------------
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
    st.subheader("How Your Money Looks This Month")

    v1, v2, v3 = st.columns(3, gap="large")

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
            top_expenses_bar(fixed_df, variable_df),
            width="stretch",
        )

    with v3:
        st.plotly_chart(
            debt_payments_vs_balances(debt_df),
            width="stretch",
        )

# ------------------------------
# DEBT BURDEN INDICATOR
# ------------------------------
def debt_burden_indicator(*, net_income: float, debt_payments: float):
    net_income = float(net_income or 0.0)
    debt_payments = max(float(debt_payments or 0.0), 0.0)

    ratio = (debt_payments / net_income) if net_income > 0 else 0.0
    pct = ratio * 100.0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={
                "suffix": "%", 
                "valueformat": ".1f",
                "font": {"size": 34},
            },
            title=None,
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {
                    "range": [0, 60],
                    "tickfont": {"size": 12},
                },
                "bar": {"thickness": 0.25},
                "steps": [
                    {"range": [0, 15]},
                    {"range": [15, 30]},
                    {"range": [30, 60]},
                ],
                "threshold": {
                    "line": {"width": 4},
                    "thickness": 0.85,
                    "value": pct,
                },
            },
        )
    )

    fig.update_layout(
        height=190,
        margin=dict(l=10, r=10, t=10, b=10),
    )

    return fig, pct


# ------------------------------
# DEBT PAYOFF ORDER (Avalanche vs Snowball)
# ------------------------------
def debt_payoff_order_chart(debt_df: pd.DataFrame, *, strategy: str = "Avalanche (APR)"):
    """
    Ranks debts for payoff planning.

    Avalanche: highest APR first
    Snowball: smallest balance first

    Requires columns: Debt, Balance, APR %
    """
    df = debt_df.copy()

    needed = {"Debt", "Balance", "APR %"}
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.warning(f"Payoff chart skipped: missing columns {missing}")
        return go.Figure()

    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce").fillna(0.0)
    df["APR %"] = pd.to_numeric(df["APR %"], errors="coerce").fillna(0.0)

    # Keep rows that have any useful info
    df = df[(df["Balance"] > 0) | (df["APR %"] > 0)]
    if df.empty:
        return go.Figure()

    if strategy == "Snowball (Balance)":
        df = df.sort_values(["Balance", "APR %"], ascending=[True, False])
        title = "Payoff Order (Snowball: Smallest Balance First)"
        sort_key = "Balance"
    else:
        df = df.sort_values(["APR %", "Balance"], ascending=[False, True])
        title = "Payoff Order (Avalanche: Highest APR First)"
        sort_key = "APR %"

    # take top N for readability
    df = df.head(10)

    # Bar = Balance, annotated with APR (or vice versa)
    fig = go.Figure(
        go.Bar(
            x=df["Balance"],
            y=df["Debt"],
            orientation="h",
            customdata=df["APR %"],
            hovertemplate="%{y}<br>Balance: $%{x:,.0f}<br>APR: %{customdata:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16)),
        height=320,
        margin=dict(l=140, r=20, t=55, b=20),
        xaxis=dict(tickprefix="$", separatethousands=True, title="Balance"),
        yaxis=dict(autorange="reversed", title=""),
    )

    # If the user chose avalanche, add a small visual cue by showing APR text on bars
    # (Plotly doesn't need colors to make this useful.)
    fig.update_traces(
        text=[f"{apr:.1f}%" for apr in df["APR %"]],
        textposition="outside",
        cliponaxis=False,
    )

    return fig