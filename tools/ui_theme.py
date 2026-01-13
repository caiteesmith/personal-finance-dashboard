st.markdown(
    """
    <style>
      /* ---------- App canvas ---------- */
      .stApp {
        background:
          radial-gradient(1000px 500px at 10% 0%, rgba(34,197,94,.10), transparent 55%),
          radial-gradient(900px 450px at 90% 10%, rgba(99,102,241,.08), transparent 55%),
          linear-gradient(180deg, #0B0F1A 0%, #020617 100%);
      }

      /* ---------- Containers / cards ---------- */
      div[data-testid="stExpander"] > details,
      div[data-testid="metric-container"],
      div[data-testid="stDataFrame"] {
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,.08);
        background: rgba(17,24,39,.85);
        box-shadow: 0 12px 32px rgba(0,0,0,.45);
      }

      /* ---------- Metrics ---------- */
      div[data-testid="metric-container"] label {
        color: #9CA3AF;
        letter-spacing: .02em;
      }
      div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #E5E7EB;
        font-weight: 600;
      }

      /* ---------- Tabs ---------- */
      button[data-baseweb="tab"] {
        border-radius: 999px !important;
        background: rgba(255,255,255,.04) !important;
        border: 1px solid rgba(255,255,255,.06) !important;
        margin-right: .35rem;
      }
      button[data-baseweb="tab"][aria-selected="true"] {
        background: rgba(34,197,94,.15) !important;
        border-color: rgba(34,197,94,.35) !important;
      }

      /* ---------- Inputs ---------- */
      .stTextInput input,
      .stNumberInput input,
      .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 14px !important;
        background-color: #020617 !important;
        border: 1px solid rgba(255,255,255,.08) !important;
      }

      /* ---------- Buttons ---------- */
      button[kind="primary"] {
        border-radius: 999px !important;
        background: linear-gradient(180deg, #22C55E, #16A34A);
        box-shadow: 0 10px 30px rgba(34,197,94,.35);
      }

      /* ---------- Sidebar ---------- */
      section[data-testid="stSidebar"] {
        background: rgba(2,6,23,.85);
        border-right: 1px solid rgba(255,255,255,.08);
      }

      /* ---------- Dividers ---------- */
      hr {
        border: none;
        height: 1px;
        background: rgba(255,255,255,.08);
      }
    </style>
    """,
    unsafe_allow_html=True,
)