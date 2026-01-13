import streamlit as st

def render_finance_theme_dark():
  st.markdown(
    """
    <style>
      /* ---------- Cards ---------- */
      div[data-testid="stExpander"] > details,
      div[data-testid="metric-container"],
      div[data-testid="stDataFrame"] {
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,.06);
        background: #161B22;
      }

      /* ---------- Buttons (squoval, not pills) ---------- */
      button[kind="primary"],
      button[kind="secondary"] {
        border-radius: 10px !important;
        padding: .45rem .85rem;
        font-weight: 500;
      }

      /* ---------- Tabs ---------- */
      button[data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: .35rem .75rem;
      }

      /* ---------- Inputs ---------- */
      .stTextInput input,
      .stNumberInput input,
      .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 10px !important;
      }

      /* ---------- Data editor cells ---------- */
      div[data-testid="stDataFrame"] * {
        border-radius: 0px;
      }

      /* ---------- Dividers ---------- */
      hr {
        border: none;
        height: 1px;
        background: rgba(255,255,255,.06);
      }
    </style>
    """,
    unsafe_allow_html=True,
)