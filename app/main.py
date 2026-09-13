import streamlit as st
import os
import time
import pandas as pd
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio, get_audio_duration

_APP_DIR = Path(__file__).resolve().parent
load_dotenv(_APP_DIR / ".env")

  
def main():
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )

    load_css(str(_APP_DIR / "static" / "style.css"))
    inject_local_font(str(_APP_DIR / "static" / "AdobeClean.otf"), "AdobeClean")

    init_db()

    if not render_login_wall():
        return 

    initial_session_defaults()

    if "voice_pipeline" not in st.session_state:
        api_key = os.environ.get("GROQ_API_KEY", "")

        if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]

        if not api_key:
            st.session_state.voice_pipeline = None
        else:
            try:
                groq_client = Groq(api_key=api_key)
                llm_coach = LLMCoach(groq_client)
                tts = TextToSpeech()
                st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
            except Exception as e:
                print(f"[MainApp Warning] Voice pipeline init error: {e}")
                st.session_state.voice_pipeline = None

    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("🏋️‍♂️ Apna AI Coach")

        if st.session_state.username:
            st.caption(f"👤 Login as {st.session_state.username}")

        st.divider()

        st.subheader("Workout Plan")

        if not workout_started:
            plan_exercise = st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")

            vp = st.session_state.get("voice_pipeline")
            if plan_exercise != st.session_state.get("last_plan_exercise"):
                st.session_state.last_plan_exercise = plan_exercise
                st.session_state.coach_feedback = None
                st.session_state.audio_to_play = None
                st.session_state.audio_expires_at = 0.0
                st.session_state.audio_event_id = 0
                st.session_state.last_played_audio_id = 0
                st.session_state.workout_completed = False
                st.session_state.workout_incomplete = False
                st.session_state.workout_ending = False
                if vp is not None:
                    vp.reset()

            plan_sets = st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)

            plan_reps = st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)

            st.markdown("")

            start_session_button = st.button("Start Workout", width="stretch", key="start_session_button")

            if start_session_button:
                target_sets_val = int(plan_sets)
                reps_per_set_val = int(plan_reps)

                if target_sets_val <= 0 or reps_per_set_val <= 0:
                    st.error("Please configure Sets and Reps per Set greater than 0 before starting.")
                else:
                    st.session_state.exercise_type = plan_exercise
                    st.session_state.target_sets = target_sets_val
                    st.session_state.reps_per_set = reps_per_set_val
                    st.session_state.reps = 0
                    st.session_state.detector_last_raw_reps = 0
                    st.session_state.sets_completed = 0
                    st.session_state.current_set_reps = 0
                    st.session_state.workout_completed = False
                    st.session_state.workout_incomplete = False
                    st.session_state.workout_ending = False
                    st.session_state.coach_feedback = None
                    st.session_state.audio_to_play = None
                    st.session_state.audio_expires_at = 0.0
                    st.session_state.audio_event_id = 0
                    st.session_state.last_played_audio_id = 0
                    st.session_state.workout_started = True
                    st.session_state.set_cycle_started_at = time.time()
                    st.session_state.last_saved_sets_completed = 0
                    st.session_state.last_notified_sets_completed = 0
                    st.session_state.last_notified_workout_complete = False

                    if vp is not None:
                        vp.reset()
                        result = vp.process_event(
                            event="workout_started",
                            exercise=plan_exercise,
                            metrics={}
                        )
                        
                        if result:
                            st.session_state.audio_to_play, st.session_state.coach_feedback = result
                            st.session_state.audio_event_id = time.time()
                            st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5

                    st.rerun()
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** -- {sets} sets X {reps} reps")

            workout_ending = st.session_state.get("workout_ending", False)

            if workout_ending:
                st.button("Ending Workout...", disabled=True, width="stretch", key="ending_session_button")
            else:
                end_session_button = st.button("End Workout", key="end_session_button", width="stretch")

                if end_session_button:
                    target_sets_val = st.session_state.get("target_sets", 0)
                    reps_per_set_val = st.session_state.get("reps_per_set", 0)
                    total_reps = st.session_state.get("reps", 0)
                    is_completed = st.session_state.get("workout_completed", False)
                    already_notified = st.session_state.get("last_notified_workout_complete", False)

                    completed_sets = (total_reps // reps_per_set_val) if reps_per_set_val > 0 else 0
                    partial_reps = (total_reps % reps_per_set_val) if reps_per_set_val > 0 else 0

                    genuinely_completed = bool(
                        is_completed or (target_sets_val > 0 and completed_sets >= target_sets_val and total_reps > 0)
                    )

                    st.session_state.workout_ending = True

                    vp = st.session_state.get("voice_pipeline")
                    if vp is not None:
                        if genuinely_completed:
                            st.session_state.workout_completed = True
                            st.session_state.workout_incomplete = False
                            if not already_notified:
                                st.session_state.last_notified_workout_complete = True
                                result = vp.process_event(
                                    event="workout_completed",
                                    exercise=exercise,
                                    metrics={"reps": total_reps, "sets_completed": completed_sets, "target_sets": target_sets_val}
                                )
                                if result:
                                    st.session_state.audio_to_play, st.session_state.coach_feedback = result
                                    st.session_state.audio_event_id = time.time()
                                    st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5
                        else:
                            st.session_state.workout_completed = False
                            st.session_state.workout_incomplete = True
                            st.session_state.sets_completed = completed_sets
                            st.session_state.current_set_reps = partial_reps
                            if not already_notified:
                                st.session_state.last_notified_workout_complete = True
                                result = vp.process_event(
                                    event="workout_aborted",
                                    exercise=exercise,
                                    metrics={
                                        "reps": total_reps,
                                        "sets_completed": completed_sets,
                                        "partial_reps": partial_reps,
                                        "target_sets": target_sets_val,
                                    }
                                )
                                if result:
                                    st.session_state.audio_to_play, st.session_state.coach_feedback = result
                                    st.session_state.audio_event_id = time.time()
                                    st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5

                        vp.reset()
                    else:
                        st.session_state.last_notified_workout_complete = True

                    st.rerun()

        if workout_started:
            st.divider()

            exercise = st.session_state.get("exercise_type")
            total_reps = st.session_state.get("reps")
            current_set_reps = st.session_state.get("current_set_reps")
            reps_per_set = st.session_state.get("reps_per_set")
            sets_completed = st.session_state.get("sets_completed")
            target_sets = st.session_state.get("target_sets")

            st.subheader("Progress")

            st.metric("Total Reps", f"{total_reps}")
            st.metric("Current Set Reps", f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets Completed", f"{sets_completed} / {target_sets}")

            st.divider()

            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                st.metric("Back Angle", f"{st.session_state.back_angle}°")
                st.metric("Depth Status", st.session_state.depth_status)

            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Body Alignment", st.session_state.body_alignment)
                st.metric("Hip Position", st.session_state.hip_status)

            elif exercise == "Biceps Curls (Dumbbell)":
                st.subheader("Curl Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Shoulder Stability", st.session_state.shoulder_status)
                st.metric("Swing Detection", st.session_state.swing_status)

            elif exercise == "Shoulder Press":
                st.subheader("Shoulder Press Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Arm Extension", st.session_state.extension_status)
                st.metric("Back Arch", st.session_state.back_arch_status)

            elif exercise == "Lunges":
                st.subheader("Lunge Metrics")
                st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                st.metric("Balance Status", st.session_state.balance_status)

    st.title("AI Real-time GYM Coach")
    st.markdown("#### Real-time pose detection with proactive AI voice coaching")
 
    # Fixed, stable placeholder for Coach Feedback (never duplicates, never shifts camera)
    coach_placeholder = st.empty()
    if st.session_state.get("coach_feedback"):
        coach_placeholder.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")
    else:
        coach_placeholder.empty()

    context = None
    if not workout_started:
        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
                margin-bottom: 32px;
            ">
                <h2 style="color:#ccc; margin-bottom:8px;">👈 Set your workout plan</h2>
                <p style="font-size:1.05rem;">
                    Choose your exercise, sets and reps in the sidebar,<br>
                    then click <strong>Start Workout</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )

        sync_metrics_update(context)
        inject_webrtc_styles()

    # Fixed, stable placeholder for Audio Playback (placed AFTER camera so audio changes never shift camera position)
    audio_placeholder = st.empty()
    active_audio = st.session_state.get("audio_to_play")
    audio_event_id = st.session_state.get("audio_event_id", 0)
    last_played_id = st.session_state.get("last_played_audio_id", 0)

    if active_audio:
        if audio_event_id != last_played_id:
            st.session_state.last_played_audio_id = audio_event_id
            autoplay_audio(active_audio, container=audio_placeholder)
        elif time.time() >= st.session_state.get("audio_expires_at", 0.0):
            st.session_state.audio_to_play = None
            st.session_state.audio_expires_at = 0.0
            audio_placeholder.empty()
    else:
        audio_placeholder.empty()

    # Final workout completion / early-end shutdown:
    # Camera state and ending audio state are decoupled.
    # Whether camera is streaming or already stopped, allow final coaching audio to play completely.
    # Shut down workout state and return to home/setup ONLY after final audio lifecycle has finished.
    is_ending = bool(st.session_state.get("workout_ending", False) or st.session_state.get("workout_completed", False))
    final_notified = bool(st.session_state.get("last_notified_workout_complete", False))
    audio_finished = bool(st.session_state.get("audio_to_play") is None or time.time() >= st.session_state.get("audio_expires_at", 0.0))

    if workout_started and is_ending:
        if final_notified and audio_finished:
            st.session_state.workout_started = False
            st.session_state.workout_ending = False
            st.session_state.audio_to_play = None
            st.session_state.audio_expires_at = 0.0
            audio_placeholder.empty()
            st.rerun()

    st.divider()

    st.markdown("#### Workout History")

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id, int):
        history_rows = get_users_exercises(user_id)

        arr = [
            {
                "Exercise": row['exercise_name'],
                "Reps": row['reps'],
                "Sets": row['sets'],
                "Time (sec)": row['time'],
                "Date": row['created_at']
            }
            for row in history_rows
        ]

        df = pd.DataFrame(arr)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            agg_df = df.groupby(["Exercise", "Date"]).agg({
                "Reps": 'sum',
                "Sets": "sum",
                "Time (sec)": "sum"
            }).reset_index()
            agg_df.index += 1
            st.table(agg_df, border="horizontal")
        else:
            st.info("No workout history found.")

    # Periodic frame refresh when WebRTC streaming is active OR when ending flow is waiting for final audio
    should_rerun = False
    if workout_started:
        if context is not None and hasattr(context, "state") and context.state.playing:
            should_rerun = True
        elif is_ending and not audio_finished:
            should_rerun = True

    if should_rerun:
        time.sleep(0.25)
        st.rerun()


if __name__ == "__main__":
    main()
    