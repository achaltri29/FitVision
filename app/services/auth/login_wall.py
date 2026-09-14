import streamlit as st
from services.persistence.exercise_repository import get_or_create_user


def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    # FitVision welcome portal header
    st.markdown(
        """
        <div style="text-align: center; padding: 32px 0 8px 0;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🏋️‍♂️</div>
            <h1 style="font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
                       color: #E8EAF0; margin: 0 auto 4px auto; text-align: center; line-height: 1.2;
                       position: relative; left: +15px;">
                FitVision
            </h1>
            <p style="font-size: 0.9rem; color: #6B7280; margin: 0 0 4px 0;
                      letter-spacing: 0.04em; text-transform: uppercase; font-weight: 500;">
                AI Workout Coach
            </p>
            <p style="font-size: 0.88rem; color: #4B5563; margin: 12px auto 0; max-width: 360px;
                      line-height: 1.6;">
                Real-time pose detection and proactive AI voice coaching.<br>
                Enter a unique username to begin your session.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="e.g. alex_fitness")
        submit_button = st.form_submit_button("Start Session", width="stretch")

    if submit_button:
        if not username:
            st.error("Username cannot be empty.")
            return False
        
        user = get_or_create_user(username)
    
        st.session_state["user_id"] = user["id"]
        st.session_state["username"] = user["username"]

        st.rerun()

    return False