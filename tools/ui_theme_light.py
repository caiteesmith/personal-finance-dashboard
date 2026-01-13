import streamlit as st

def render_finance_theme_light():
    st.markdown(
        """
        <style>
          /* ---------- App canvas ---------- */
          .stApp {
            background: radial-gradient(1200px 600px at 10% 0%, rgba(99,102,241,.10), transparent 60%),
                        radial-gradient(1000px 500px at 90% 10%, rgba(16,185,129,.10), transparent 55%),
                        linear-gradient(180deg, #FBFCFE 0%, #F7F8FB 100%);
          }

          /* ---------- Typography ---------- */
          html, body, [class*="css"]  {
            font-feature-settings: "ss01" 1, "cv02" 1;
          }

          /* ---------- Page header spacing ---------- */
          .block-container {
            padding-top: 2.25rem;
            padding-bottom: 2.25rem;
            max-width: 1200px;
          }

          /* ---------- Cards (expanders / containers) ---------- */
          div[data-testid="stExpander"] > details {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, .08);
            background: rgba(255,255,255,.82);
            box-shadow: 0 10px 28px rgba(15, 23, 42, .06);
            overflow: hidden;
          }
          div[data-testid="stExpander"] summary {
            padding: .85rem 1rem;
            font-weight: 600;
          }

          /* ---------- Metric cards ---------- */
          div[data-testid="metric-container"] {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, .08);
            background: rgba(255,255,255,.82);
            box-shadow: 0 10px 28px rgba(15, 23, 42, .06);
            padding: 14px 14px 10px 14px;
          }
          div[data-testid="metric-container"] label {
            font-size: 0.85rem;
            opacity: .85;
          }
          div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.6rem;
            line-height: 1.1;
          }

          /* ---------- Tabs ---------- */
          button[data-baseweb="tab"] {
            border-radius: 999px !important;
            margin-right: .35rem;
            padding: .4rem .85rem;
          }
          button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(99,102,241,.12) !important;
            border: 1px solid rgba(99,102,241,.25) !important;
          }

          /* ---------- Inputs ---------- */
          .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 14px !important;
          }

          /* ---------- Buttons ---------- */
          button[kind="primary"] {
            border-radius: 999px !important;
            padding: .55rem 1rem !important;
            box-shadow: 0 10px 24px rgba(99,102,241,.18);
          }
          button[kind="secondary"] {
            border-radius: 999px !important;
          }

          /* ---------- Data editor / tables ---------- */
          div[data-testid="stDataFrame"] {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, .08);
            background: rgba(255,255,255,.82);
            box-shadow: 0 10px 28px rgba(15, 23, 42, .06);
            overflow: hidden;
          }

          /* ---------- Section dividers ---------- */
          hr {
            margin: 1.25rem 0;
            border: none;
            height: 1px;
            background: rgba(15, 23, 42, .10);
          }

          /* ---------- Sidebar (optional, but looks nice) ---------- */
          section[data-testid="stSidebar"] {
            background: rgba(255,255,255,.70);
            border-right: 1px solid rgba(15, 23, 42, .08);
          }
          section[data-testid="stSidebar"] .block-container {
            padding-top: 1.25rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )