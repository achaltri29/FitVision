import streamlit as st


def initial_session_defaults():
    defaults = {
        "reps": 0,
        "target_sets": 0,
        "reps_per_set": 0,
        "sets_completed": 0,
        "current_set_reps": 0,
        "workout_complete": False,
        "workout_completed": False,
        "workout_incomplete": False,
        "workout_ending": False,
        "last_notified_sets_completed": 0,
        "last_notified_workout_complete": False,
        "last_saved_sets_completed": 0,
        "set_cycle_started_at": 0.0,
        "last_exercise_type": "Squats",
        "last_plan_exercise": "Squats",
        "coach_feedback": None,
        "audio_to_play": None,
        "audio_expires_at": 0.0,
        "audio_event_id": 0,
        "last_played_audio_id": 0,
        "detector_last_raw_reps": 0,

        # Workout plan (set before starting)
        "workout_started": False,
        "plan_exercise": "Squats",
        "plan_sets": 3,
        "plan_reps": 10,

        # Common Angles & Metrics
        "knee_angle": 0,
        "back_angle": 0,
        "elbow_angle": 0,
        "front_knee_angle": 0,
        "torso_angle": 0,
        "arm_angle": 0,
        "stance_ratio": 0.0,
        "knee_height": 0,
        "torso_lean_angle": 0,
        "left_compression": 0.0,
        "right_compression": 0.0,
        "lateral_flexion": 0,

        # Status fields
        "depth_status": "N/A",
        "body_alignment": "N/A",
        "hip_status": "N/A",
        "shoulder_status": "N/A",
        "swing_status": "N/A",
        "extension_status": "N/A",
        "back_arch_status": "N/A",
        "balance_status": "N/A",
        "arm_status": "N/A",
        "stance_status": "N/A",
        "sync_status": "N/A",
        "knee_status": "N/A",
        "active_leg": "N/A",
        "torso_status": "N/A",
        "active_side": "NONE",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
