import streamlit as st
from tools.pf_state import sanitize_editor_df

def render_saveinvest_tab():
    with st.form("pf_saveinvest_form", border=False):
        st.write("Monthly contributions you want to make.")
        with st.expander("Retirement benchmark", expanded=False):
            st.caption(
                "Many planners suggest ~10–20% of **gross income** toward retirement over a career "
                "(including employer match). This is a reference point, not a rule."
            )

        # s_col, i_col = st.columns(2, gap="large")

        # with s_col:
        st.markdown("**Saving**")
        saving_edit = st.data_editor(
            st.session_state["pf_saving_df"],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="pf_saving_editor",
            column_config={"Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f")},
        )

        # with i_col:
        st.markdown("**Investing**")
        investing_edit = st.data_editor(
            st.session_state["pf_investing_df"],
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="pf_investing_editor",
            column_config={"Monthly Amount": st.column_config.NumberColumn(min_value=0.0, step=25.0, format="%.2f")},
        )

        submitted = st.form_submit_button("Save saving & investing", type="primary", width="stretch")

    if submitted:
        st.session_state["pf_saving_df"] = sanitize_editor_df(
            saving_edit, expected_cols=["Bucket", "Monthly Amount", "Notes"], numeric_cols=["Monthly Amount"]
        )
        st.session_state["pf_investing_df"] = sanitize_editor_df(
            investing_edit, expected_cols=["Bucket", "Monthly Amount", "Notes"], numeric_cols=["Monthly Amount"]
        )
        st.rerun()