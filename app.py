# =========================================
# file: app.py
# =========================================
from __future__ import annotations

import streamlit as st

from tools.finance_dashboard import render_personal_finance_dashboard
from tools.mortgage_payoff import render_mortgage_payoff_calculator
from tools.about import render_about

def main():
    st.set_page_config(page_title="Financial Breakdown", layout="wide")

    # Sidebar navigation
    st.sidebar.title("Financial Breakdown")
    page = st.sidebar.radio(
        "Go to",
        ["About Financial Breakdown", "Personal Finance Dashboard", "Mortgage Payoff Calculator"],
        index=0,
        key="nav_page"
    )

    if page == "Personal Finance Dashboard":
        render_personal_finance_dashboard()
    elif page == "Mortgage Payoff Calculator":
        render_mortgage_payoff_calculator()
    else:
        render_about()


if __name__ == "__main__":
    main()