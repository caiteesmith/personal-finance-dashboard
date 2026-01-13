from __future__ import annotations

import streamlit as st

from tools.finance_dashboard import render_personal_finance_dashboard
from tools.ui_theme_dark import render_finance_theme_dark

st.set_page_config(
    page_title="Personal Finance Dashboard",
    page_icon="assets/favicon.png",
    layout="wide",
)

def main():
    render_finance_theme_dark()
    render_personal_finance_dashboard()


if __name__ == "__main__":
    main()