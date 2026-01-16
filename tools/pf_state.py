from __future__ import annotations

from datetime import datetime
from typing import Dict, List
import json
import hashlib
import pandas as pd
import streamlit as st


# -------------------------
# Helpers
# -------------------------
def money(x: float) -> str:
    return f"${float(x or 0.0):,.2f}"


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.1f}%"


def safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def sum_df(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def ensure_df(key: str, default_rows: List[Dict]) -> pd.DataFrame:
    if key not in st.session_state or not isinstance(st.session_state[key], pd.DataFrame):
        st.session_state[key] = pd.DataFrame(default_rows)
    return st.session_state[key]


def sanitize_editor_df(df: pd.DataFrame, expected_cols: List[str], numeric_cols: List[str]) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=expected_cols)

    drop_candidates = {"id", "_id", "__id", "row_id", "_row_id", "index", "__index__"}
    extra = [c for c in df.columns if str(c).strip().lower() in drop_candidates]
    if extra:
        df = df.drop(columns=extra, errors="ignore")

    for c in expected_cols:
        if c not in df.columns:
            df[c] = "" if c not in numeric_cols else 0.0

    df = df[expected_cols].copy()

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    df = df.reset_index(drop=True)
    return df


# -------------------------
# Snapshot load/apply
# -------------------------
def load_snapshot_into_state(snapshot: dict):
    """
    Loads snapshot data into st.session_state.
    Only supports the new schema: fixed + essential + non-essential.
    """
    if not isinstance(snapshot, dict):
        return

    st.session_state["pf_month_label"] = snapshot.get("month_label", st.session_state.get("pf_month_label"))

    settings = snapshot.get("settings", {}) or {}
    if "income_is" in settings:
        st.session_state["pf_income_is"] = settings.get("income_is") or st.session_state.get("pf_income_is", "Net (after tax)")
    if "gross_mode" in settings:
        st.session_state["pf_gross_mode"] = settings.get("gross_mode") or st.session_state.get("pf_gross_mode", "Estimate (tax rate)")
    if "tax_rate_pct" in settings:
        st.session_state["pf_tax_rate"] = safe_float(settings.get("tax_rate_pct", st.session_state.get("pf_tax_rate", 0.0)))

    gb = snapshot.get("gross_breakdown_optional", {}) or {}
    st.session_state["pf_manual_taxes"] = safe_float(gb.get("taxes", 0))
    st.session_state["pf_manual_retirement"] = safe_float(gb.get("retirement_employee", 0))
    st.session_state["pf_manual_match"] = safe_float(gb.get("company_match", 0))
    st.session_state["pf_manual_benefits"] = safe_float(gb.get("benefits", 0))
    st.session_state["pf_manual_other_ssi"] = safe_float(gb.get("other_ssi", 0))

    gb = snapshot.get("gross_breakdown_optional", {}) or {}
    st.session_state["pf_manual_taxes"] = safe_float(gb.get("taxes", 0))
    st.session_state["pf_manual_retirement"] = safe_float(gb.get("retirement_employee", 0))
    st.session_state["pf_manual_match"] = safe_float(gb.get("company_match", 0))
    st.session_state["pf_manual_benefits"] = safe_float(gb.get("benefits", 0))
    st.session_state["pf_manual_other_ssi"] = safe_float(gb.get("other_ssi", 0))

    # Keep paycheck breakdown drafts in sync with manual values
    st.session_state["pf_draft_taxes"] = st.session_state["pf_manual_taxes"]
    st.session_state["pf_draft_retirement"] = st.session_state["pf_manual_retirement"]
    st.session_state["pf_draft_match"] = st.session_state["pf_manual_match"]
    st.session_state["pf_draft_benefits"] = st.session_state["pf_manual_benefits"]
    st.session_state["pf_draft_other_ssi"] = st.session_state["pf_manual_other_ssi"]

    tables = snapshot.get("tables", {}) or {}

    def _set_table(key: str, rows: list[dict], expected_cols: list[str], numeric_cols: list[str]):
        df = pd.DataFrame(rows or [])
        st.session_state[key] = sanitize_editor_df(df, expected_cols=expected_cols, numeric_cols=numeric_cols)

    _set_table("pf_income_df", tables.get("income"), ["Source", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_fixed_df", tables.get("fixed_expenses"), ["Expense", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_essential_df", tables.get("essential_expenses"), ["Expense", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_nonessential_df", tables.get("nonessential_expenses"), ["Expense", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_saving_df", tables.get("saving"), ["Bucket", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_investing_df", tables.get("investing"), ["Bucket", "Monthly Amount", "Notes"], ["Monthly Amount"])
    _set_table("pf_assets_df", tables.get("assets"), ["Asset", "Value", "Notes"], ["Value"])
    _set_table("pf_liabilities_df", tables.get("liabilities"), ["Liability", "Value", "Notes"], ["Value"])
    _set_table("pf_debt_df", tables.get("debt_details"),
               ["Debt", "Balance", "APR %", "Monthly Payment", "Notes"],
               ["Balance", "APR %", "Monthly Payment"])


def apply_pending_snapshot_if_any() -> None:
    """
    If there's a snapshot waiting in session_state["pf_pending_snapshot"],
    apply it to the various pf_* tables & settings, then clear the flag.
    """
    if not st.session_state.get("pf_has_pending_import"):
        return

    snap = st.session_state.get("pf_pending_snapshot")
    if not isinstance(snap, dict):
        # Nothing usable; clear and bail.
        st.session_state["pf_has_pending_import"] = False
        st.session_state.pop("pf_pending_snapshot", None)
        return

    # ----- Core tables -----
    tables = snap.get("tables", {})
    def _to_df(records, cols):
        if not isinstance(records, list):
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame.from_records(records)
        # ensure all expected cols exist
        for c in cols:
            if c not in df.columns:
                df[c] = 0.0 if c != "Notes" else ""
        return df[cols]

    st.session_state["pf_income_df"] = _to_df(tables.get("income"), ["Source", "Monthly Amount", "Notes"])
    st.session_state["pf_fixed_df"] = _to_df(tables.get("fixed_expenses"), ["Expense", "Monthly Amount", "Notes"])
    st.session_state["pf_essential_df"] = _to_df(tables.get("essential_expenses"), ["Expense", "Monthly Amount", "Notes"])
    st.session_state["pf_nonessential_df"] = _to_df(tables.get("nonessential_expenses"), ["Expense", "Monthly Amount", "Notes"])
    st.session_state["pf_saving_df"] = _to_df(tables.get("saving"), ["Bucket", "Monthly Amount", "Notes"])
    st.session_state["pf_investing_df"] = _to_df(tables.get("investing"), ["Bucket", "Monthly Amount", "Notes"])
    st.session_state["pf_assets_df"] = _to_df(tables.get("assets"), ["Asset", "Value", "Notes"])
    st.session_state["pf_liabilities_df"] = _to_df(tables.get("liabilities"), ["Liability", "Value", "Notes"])
    st.session_state["pf_debt_df"] = _to_df(
        tables.get("debt_details"),
        ["Debt", "Balance", "APR %", "Monthly Payment", "Notes"],
    )

    # ----- Settings / metadata -----
    settings = snap.get("settings", {})
    st.session_state["pf_month_label"] = snap.get("month_label", st.session_state.get("pf_month_label", ""))
    st.session_state["pf_income_is"] = settings.get("income_is", st.session_state.get("pf_income_is", "Net (after tax)"))
    st.session_state["pf_tax_rate"] = float(settings.get("tax_rate_pct", st.session_state.get("pf_tax_rate", 0.0)) or 0.0)
    st.session_state["pf_gross_mode"] = settings.get("gross_mode", st.session_state.get("pf_gross_mode", "Estimate (tax rate)"))

    # Optional gross breakdown fields
    gross = snap.get("gross_breakdown_optional", {})
    st.session_state["pf_manual_taxes"] = float(gross.get("taxes", 0.0) or 0.0)
    st.session_state["pf_manual_retirement"] = float(gross.get("retirement_employee", 0.0) or 0.0)
    st.session_state["pf_manual_match"] = float(gross.get("company_match", 0.0) or 0.0)
    st.session_state["pf_manual_benefits"] = float(gross.get("benefits", 0.0) or 0.0)
    st.session_state["pf_manual_other_ssi"] = float(gross.get("other_ssi", 0.0) or 0.0)

    # Sync paycheck breakdown *draft* fields so the UI repopulates correctly
    st.session_state["pf_draft_taxes"] = st.session_state["pf_manual_taxes"]
    st.session_state["pf_draft_retirement"] = st.session_state["pf_manual_retirement"]
    st.session_state["pf_draft_match"] = st.session_state["pf_manual_match"]
    st.session_state["pf_draft_benefits"] = st.session_state["pf_manual_benefits"]
    st.session_state["pf_draft_other_ssi"] = st.session_state["pf_manual_other_ssi"]

    # ----- Restore paycheck breakdown flag -----
    monthly = snap.get("monthly_cash_flow", {})
    st.session_state["pf_use_paycheck_breakdown"] = bool(
        monthly.get(
            "paycheck_breakdown_enabled",
            st.session_state.get("pf_use_paycheck_breakdown", False),
        )
    )

    # Clear the pending flag so we don't re-apply next run
    st.session_state["pf_has_pending_import"] = False
    st.session_state.pop("pf_pending_snapshot", None)


def snapshot_signature(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bump_uploader_nonce():
    st.session_state["pf_uploader_nonce"] = int(st.session_state.get("pf_uploader_nonce", 0)) + 1