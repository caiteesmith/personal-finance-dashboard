import streamlit as st
from tools.pf_state import sanitize_editor_df

def render_income_tab():
    st.write("Add your income sources. If you have a two-income household, include both here.")
    st.caption(
        "For paycheck-level accuracy (pre-tax 401k contributions, employer match, benefits, and taxes), "
        "use the optional toggle below."
    )

    with st.form("pf_income_form", border=False):
        income_edit = st.data_editor(
            st.session_state["pf_income_df"],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="pf_income_editor",
            column_config={
                "Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.2f"),
            },
        )
        income_submitted = st.form_submit_button("Save income", type="primary", width="stretch")

    if income_submitted:
        st.session_state["pf_income_df"] = sanitize_editor_df(
            income_edit,
            expected_cols=["Source", "Monthly Amount", "Notes"],
            numeric_cols=["Monthly Amount"],
        )
        st.rerun()

    st.markdown("---")
    st.markdown("#### Optional: Paycheck breakdown (gross → net)")
    st.caption(
        "Turn this on only if your income above is **gross** and you want the dashboard to calculate **net income** "
        "using monthly deductions."
    )

    st.toggle(
        "Use paycheck breakdown",
        key="pf_use_paycheck_breakdown",
    )

    # --- Paycheck breakdown form (prevents red 'missing submit button' flashes) ---
    with st.form("pf_paycheck_breakdown_form", border=False):
        use_breakdown = bool(st.session_state.get("pf_use_paycheck_breakdown", False))

        if use_breakdown:
            # draft defaults (safe to do here; form isolates rerun behavior)
            st.session_state.setdefault("pf_draft_taxes", float(st.session_state.get("pf_manual_taxes", 0.0) or 0.0))
            st.session_state.setdefault("pf_draft_retirement", float(st.session_state.get("pf_manual_retirement", 0.0) or 0.0))
            st.session_state.setdefault("pf_draft_benefits", float(st.session_state.get("pf_manual_benefits", 0.0) or 0.0))
            st.session_state.setdefault("pf_draft_other_ssi", float(st.session_state.get("pf_manual_other_ssi", 0.0) or 0.0))
            st.session_state.setdefault("pf_draft_match", float(st.session_state.get("pf_manual_match", 0.0) or 0.0))

            g1, g2, g3 = st.columns(3, gap="large")
            with g1:
                st.number_input("Taxes", min_value=0.0, step=50.0, key="pf_draft_taxes")
                st.number_input("Benefits", min_value=0.0, step=25.0, key="pf_draft_benefits")
            with g2:
                st.number_input("Retirement (employee)", min_value=0.0, step=50.0, key="pf_draft_retirement")
                st.number_input("Other/SSI", min_value=0.0, step=25.0, key="pf_draft_other_ssi")
            with g3:
                st.number_input(
                    "Company Match (optional)",
                    min_value=0.0,
                    step=50.0,
                    key="pf_draft_match",
                    help="Tracked as extra retirement contribution; does not reduce take-home.",
                )
        else:
            st.caption("Turn on **Use paycheck breakdown** to enter deductions and calculate net income.")

        # Submit button exists on every render of the form
        breakdown_submitted = st.form_submit_button(
            "Save breakdown",
            type="primary",
            use_container_width=True,
        )

    if breakdown_submitted:
        # if toggle is off, treat as a reset of deductions (optional, but keeps state consistent)
        if not st.session_state.get("pf_use_paycheck_breakdown", False):
            st.session_state["pf_manual_taxes"] = 0.0
            st.session_state["pf_manual_benefits"] = 0.0
            st.session_state["pf_manual_retirement"] = 0.0
            st.session_state["pf_manual_other_ssi"] = 0.0
            st.session_state["pf_manual_match"] = 0.0
        else:
            st.session_state["pf_manual_taxes"] = float(st.session_state.get("pf_draft_taxes", 0.0) or 0.0)
            st.session_state["pf_manual_benefits"] = float(st.session_state.get("pf_draft_benefits", 0.0) or 0.0)
            st.session_state["pf_manual_retirement"] = float(st.session_state.get("pf_draft_retirement", 0.0) or 0.0)
            st.session_state["pf_manual_other_ssi"] = float(st.session_state.get("pf_draft_other_ssi", 0.0) or 0.0)
            st.session_state["pf_manual_match"] = float(st.session_state.get("pf_draft_match", 0.0) or 0.0)

        st.rerun()