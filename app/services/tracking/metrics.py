import streamlit as st
import time
from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repository import add_exercise
from services.coaching.voice_pipeline import get_audio_duration


def sync_metrics_update(context):
    if not context or not hasattr(context, "state") or not context.state.playing:
        return
    
    processor = getattr(context, "video_processor", None)

    if not processor:
        return 
    
    exercise = st.session_state.get("exercise_type")

    if not exercise:
        return
    
    processor.set_exercise(exercise)
    latest_metrics = processor.get_latest_metrics()

    if not latest_metrics:
        return
    
    reps_per_set = st.session_state.get("reps_per_set", 0)
    target_sets = st.session_state.get("target_sets", 0)
    max_reps = (target_sets * reps_per_set) if (target_sets > 0 and reps_per_set > 0) else 0

    already_completed = bool(
        st.session_state.get("workout_completed", False)
        or st.session_state.get("workout_ending", False)
        or (target_sets > 0 and st.session_state.get("sets_completed", 0) >= target_sets)
    )

    raw_reps = latest_metrics.get("reps", 0)
    if raw_reps is None:
        raw_reps = 0

    last_raw = st.session_state.get("detector_last_raw_reps", 0)

    if already_completed:
        # Workout is completed or ending; freeze reps and sets to prevent over-counting
        if st.session_state.get("workout_completed", False) and max_reps > 0:
            st.session_state.reps = max_reps
            st.session_state.sets_completed = target_sets
            st.session_state.current_set_reps = 0
        st.session_state.detector_last_raw_reps = raw_reps
    else:
        if raw_reps >= last_raw:
            delta = raw_reps - last_raw
            accumulated = st.session_state.get("reps", 0) + delta
            if max_reps > 0 and accumulated >= max_reps:
                st.session_state.reps = max_reps
            else:
                st.session_state.reps = accumulated
        else:
            # Camera / processor was restarted; preserve accumulated reps and re-baseline
            pass

        st.session_state.detector_last_raw_reps = raw_reps
        reps = st.session_state.get("reps", 0)

        if reps is not None and reps_per_set > 0 and target_sets > 0:
            raw_sets = reps // reps_per_set
            sets_completed = min(raw_sets, target_sets)

            if sets_completed >= target_sets:
                sets_completed = target_sets
                current_set_reps = 0
                reps = max_reps
                workout_completed = (reps > 0)
                if workout_completed:
                    st.session_state.workout_ending = True
            else:
                current_set_reps = reps % reps_per_set
                workout_completed = False
        else:
            sets_completed = 0
            current_set_reps = 0
            workout_completed = False

        st.session_state.reps = reps
        st.session_state.sets_completed = sets_completed
        st.session_state.current_set_reps = current_set_reps
        st.session_state.workout_completed = workout_completed

    reps = st.session_state.get("reps", 0)
    sets_completed = st.session_state.get("sets_completed", 0)
    current_set_reps = st.session_state.get("current_set_reps", 0)
    workout_completed = st.session_state.get("workout_completed", False)

    fields = METRICS_FIELDS.get(exercise)

    if not fields:
        return 

    for key, default in fields.items():
        st.session_state[key] = latest_metrics.get(key, default)

    last_saved_sets = st.session_state.get("last_saved_sets_completed", 0)

    # Record newly completed sets to database (strictly bounded by target_sets)
    capped_sets = min(sets_completed, target_sets) if target_sets > 0 else sets_completed
    if target_sets > 0 and reps_per_set > 0 and capped_sets > last_saved_sets:
        newly_completed = capped_sets - last_saved_sets
        now_ts = time.time()
        started_at = st.session_state.get("set_cycle_started_at", now_ts)
        time_taken = now_ts - started_at
        user_id = st.session_state.get("user_id", 0)

        add_exercise(user_id, exercise, newly_completed * reps_per_set, newly_completed, time_taken)
        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = capped_sets

    vp = st.session_state.get("voice_pipeline")
    pose_detected = latest_metrics.get("pose_detected", True)

    # Prioritized event routing: exactly ONE coaching event per sync cycle
    if workout_completed and not st.session_state.get("last_notified_workout_complete", False):
        st.session_state.last_notified_workout_complete = True
        st.session_state.last_notified_sets_completed = sets_completed
        st.session_state.workout_ending = True

        if vp is not None:
            result = vp.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                st.session_state.audio_event_id = time.time()
                st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5

    elif not workout_completed and target_sets > 0 and reps_per_set > 0 and sets_completed > st.session_state.get("last_notified_sets_completed", 0):
        st.session_state.last_notified_sets_completed = sets_completed

        if vp is not None:
            result = vp.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                st.session_state.audio_event_id = time.time()
                st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5

    elif not workout_completed and not pose_detected and vp is not None:
        result = vp.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={"issue": "No pose detected! Please step into the camera frame."},
        )

        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
            st.session_state.audio_event_id = time.time()
            st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5

    elif not workout_completed and vp is not None:
        result = vp.process_event(
            event="ongoing_form_check",
            exercise=exercise,
            metrics=latest_metrics,
        )

        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
            st.session_state.audio_event_id = time.time()
            st.session_state.audio_expires_at = time.time() + get_audio_duration(result[0]) + 0.5
