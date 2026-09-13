import time
import streamlit as st


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0

    def _find_form_issue(self, exercise, metrics):
        if "issue" in metrics:
            return metrics["issue"]

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)
            
            if depth == "TOO HIGH":
                return "The user's squat is not deep enough — knees are not bending sufficiently."

            if isinstance(back_angle, (int, float)) and back_angle < 130:
                return "The user is leaning too far forward during the squat."

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")
            
            if alignment == "Poor Form":
                return "The user's body is not straight during the push-up."

            if hip_status == "SAGGING":
                return "The user's hips are sagging down during the push-up."

            if hip_status == "PIKED UP":
                return "The user's hips are too high — lower them to form a straight line."

        elif exercise == "Biceps Curls (Dumbbell)":
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")
            
            if swing == "SWINGING":
                return "The user is swinging their torso during the curl — keep the body still."

            if shoulder == "ELBOW DRIFTING":
                return "The user's elbow is drifting away from their side during the curl."

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")
            extension = metrics.get("extension_status", "")
            
            if back_arch == "Excessive Arch":
                return "The user is arching their lower back excessively during the press."

            if back_arch == "Slight Arch":
                return "Slight back arch detected — encourage the user to brace their core."

        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")
            
            if balance == "OFF BALANCE":
                return "The user is losing balance during the lunge — feet should be hip-width apart."

        return None

    def reset(self):
        self.last_spoken_at = 0
        if hasattr(self.llm, "reset_history"):
            self.llm.reset_history()

    def process_event(self, event, exercise, metrics):
        now = time.time()

        if event == "workout_aborted":
            reps = metrics.get("reps", 0) if metrics else 0
            sets_completed = metrics.get("sets_completed", 0) if metrics else 0
            partial_reps = metrics.get("partial_reps", 0) if metrics else 0
            target_sets = metrics.get("target_sets", 0) if metrics else 0

            if reps <= 0:
                text = "Workout ended early. No reps were completed."
            elif sets_completed == 0 and partial_reps > 0:
                rep_word = "rep" if partial_reps == 1 else "reps"
                text = f"Workout incomplete. You didn't complete a full set, but you got {partial_reps} {rep_word} in. Keep going next time!"
            elif sets_completed > 0 and partial_reps > 0:
                set_word = "set" if sets_completed == 1 else "sets"
                rep_word = "rep" if partial_reps == 1 else "reps"
                text = f"Workout incomplete. You completed {sets_completed} full {set_word} and {partial_reps} {rep_word} of the next set."
            elif sets_completed > 0 and partial_reps == 0:
                set_word = "set" if sets_completed == 1 else "sets"
                text = f"Workout ended early. You completed {sets_completed} of {target_sets} full {set_word}."
            else:
                text = f"Workout ended early. You completed {reps} reps."

            try:
                voice = self.tts.speak(text)
                self.last_spoken_at = now
                return voice, text
            except Exception as e:
                print(f"[VoicePipeline Warning] Error generating voice feedback: {e}")
                return None

        issue = self._find_form_issue(exercise, metrics)

        is_major_issue = event in ["workout_started", "set_completed", "workout_completed"]

        if not is_major_issue:
            if not issue:
                return None
            
            if now - self.last_spoken_at < 5:
                return None
            
        try:
            text = self.llm.give_feedback(event=event, exercise=exercise, issue=issue)
            voice = self.tts.speak(text)
            self.last_spoken_at = now
            return voice, text
        except Exception as e:
            print(f"[VoicePipeline Warning] Error generating voice feedback: {e}")
            return None
    

def get_audio_duration(audio_bytes):
    if not audio_bytes:
        return 0.0
    try:
        import av
        import av.container
        from io import BytesIO
        container = av.open(BytesIO(audio_bytes))
        if isinstance(container, av.container.InputContainer) and container.duration is not None:
            return float(container.duration) / av.time_base
    except Exception:
        pass
    return max(2.5, len(audio_bytes) / 4000.0)


def autoplay_audio(audio_bytes, container=None):
    if not audio_bytes:
        return
    
    import base64
    import streamlit.components.v1 as components
    b64 = base64.b64encode(audio_bytes).decode()
    js_code = f"""
    <script>
    (function() {{
        try {{
            var p = window.parent;
            var AudioCtx = (p && p.Audio) ? p.Audio : Audio;
            var a = (p && p._fitvision_audio) ? p._fitvision_audio : new AudioCtx();
            if (p) p._fitvision_audio = a;
            a.pause();
            a.src = "data:audio/mp3;base64,{b64}";
            a.currentTime = 0;
            a.play().catch(function(err) {{
                console.warn("[FitVision Audio] Autoplay prevented:", err);
            }});
        }} catch(e) {{
            console.error("[FitVision Audio] Playback error:", e);
        }}
    }})();
    </script>
    """
    if container is not None:
        with container:
            components.html(js_code, height=0)
    else:
        components.html(js_code, height=0)

