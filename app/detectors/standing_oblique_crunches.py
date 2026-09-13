import math
from core.base_exercise import BaseExercise


class StandingObliqueCrunchesDetector(BaseExercise):
    """
    Detector for Standing Oblique Crunches.
    One repetition is defined as ONE completed side crunch:
    - User performs a lateral crunch (knee rises laterally, elbow moves down toward knee,
      achieving valid normalized compression, knee elevation, and lateral displacement).
    - User returns sufficiently toward upright/standing neutral.
    - Left side crunch -> return = 1 rep.
    - Right side crunch -> return = 1 rep.
    - Alternating sequence (Left -> Right) = 2 reps.
    """
    CRUNCH_ENTER_COMPRESSION = 0.38   # normalized elbow-knee distance <= 38% torso height
    CRUNCH_EXIT_COMPRESSION = 0.65    # normalized return distance >= 65% torso height
    KNEE_LIFT_ENTER = -0.15           # normalized knee elevation relative to hip
    KNEE_LIFT_EXIT = -0.45            # normalized knee descent return threshold
    LATERAL_MIN_DISP = 0.05           # normalized lateral abduction of knee from hip midline
    MIN_VISIBILITY = 0.60

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()
        self.stage = "standing"
        self.active_side = "NONE"

    def reset(self) -> None:
        self.reps = 0
        self.stage = "standing"
        self.active_side = "NONE"

    def process(self, landmarks) -> dict:
        key_indices = [
            self.LEFT_SHOULDER, self.RIGHT_SHOULDER,
            self.LEFT_ELBOW, self.RIGHT_ELBOW,
            self.LEFT_HIP, self.RIGHT_HIP,
            self.LEFT_KNEE, self.RIGHT_KNEE,
        ]

        # 1. Ensure all primary landmarks are visible
        for idx in key_indices:
            if idx >= len(landmarks) or landmarks[idx].visibility < self.MIN_VISIBILITY:
                return {
                    "reps": self.reps,
                    "left_compression": 0.0,
                    "right_compression": 0.0,
                    "active_side": self.active_side,
                    "knee_status": "N/A",
                    "compression_status": "N/A",
                    "torso_status": "N/A",
                    "lateral_flexion": 0,
                    "stage": self.stage,
                }

        # 2. Extract landmark points
        left_shoulder = landmarks[self.LEFT_SHOULDER]
        right_shoulder = landmarks[self.RIGHT_SHOULDER]
        left_elbow = landmarks[self.LEFT_ELBOW]
        right_elbow = landmarks[self.RIGHT_ELBOW]
        left_hip = landmarks[self.LEFT_HIP]
        right_hip = landmarks[self.RIGHT_HIP]
        left_knee = landmarks[self.LEFT_KNEE]
        right_knee = landmarks[self.RIGHT_KNEE]

        # 3. Torso scale reference
        s_mid_x = (left_shoulder.x + right_shoulder.x) / 2.0
        s_mid_y = (left_shoulder.y + right_shoulder.y) / 2.0
        h_mid_x = (left_hip.x + right_hip.x) / 2.0
        h_mid_y = (left_hip.y + right_hip.y) / 2.0
        torso_height = max(math.sqrt((s_mid_x - h_mid_x) ** 2 + (s_mid_y - h_mid_y) ** 2), 0.15)

        # 4. Left side geometry
        d_left = math.sqrt((left_elbow.x - left_knee.x) ** 2 + (left_elbow.y - left_knee.y) ** 2)
        comp_left = d_left / torso_height
        knee_lift_left = (left_hip.y - left_knee.y) / torso_height
        lat_left = (abs(left_knee.x - h_mid_x) - abs(left_hip.x - h_mid_x)) / torso_height

        # 5. Right side geometry
        d_right = math.sqrt((right_elbow.x - right_knee.x) ** 2 + (right_elbow.y - right_knee.y) ** 2)
        comp_right = d_right / torso_height
        knee_lift_right = (right_hip.y - right_knee.y) / torso_height
        lat_right = (abs(right_knee.x - h_mid_x) - abs(right_hip.x - h_mid_x)) / torso_height

        # 6. Torso lateral flexion angle
        dx_torso = s_mid_x - h_mid_x
        dy_torso = max(abs(s_mid_y - h_mid_y), 1e-5)
        lateral_flexion_deg = math.degrees(math.atan2(abs(dx_torso), dy_torso))

        # 7. Active side determination
        if self.stage == "left_crunch":
            active_side = "LEFT"
        elif self.stage == "right_crunch":
            active_side = "RIGHT"
        elif comp_left < comp_right and (comp_left <= 0.60 or knee_lift_left >= -0.35):
            active_side = "LEFT"
        elif comp_right < comp_left and (comp_right <= 0.60 or knee_lift_right >= -0.35):
            active_side = "RIGHT"
        else:
            active_side = "NONE"

        self.active_side = active_side

        # 8. Knee status and compression status evaluation
        if active_side == "LEFT":
            act_lift = knee_lift_left
            act_comp = comp_left
        elif active_side == "RIGHT":
            act_lift = knee_lift_right
            act_comp = comp_right
        else:
            act_lift = max(knee_lift_left, knee_lift_right)
            act_comp = min(comp_left, comp_right)

        if act_lift >= self.KNEE_LIFT_ENTER:
            knee_status = "HIGH"
        elif act_lift >= -0.35:
            knee_status = "MODERATE"
        elif active_side != "NONE":
            knee_status = "LOW"
        else:
            knee_status = "GROUND"

        if act_comp <= self.CRUNCH_ENTER_COMPRESSION:
            compression_status = "GOOD"
        elif act_comp <= 0.55:
            compression_status = "MODERATE"
        else:
            compression_status = "INSUFFICIENT"

        # 9. Torso compensation check
        if lateral_flexion_deg >= 25.0 and act_lift < -0.20:
            torso_status = "EXCESSIVE LEAN"
        else:
            torso_status = "CONTROLLED"

        # 10. Hysteresis State Machine
        left_qualifies = (
            comp_left <= self.CRUNCH_ENTER_COMPRESSION
            and knee_lift_left >= self.KNEE_LIFT_ENTER
            and lat_left >= self.LATERAL_MIN_DISP
        )
        right_qualifies = (
            comp_right <= self.CRUNCH_ENTER_COMPRESSION
            and knee_lift_right >= self.KNEE_LIFT_ENTER
            and lat_right >= self.LATERAL_MIN_DISP
        )

        if self.stage == "standing":
            if left_qualifies:
                self.stage = "left_crunch"
                self.active_side = "LEFT"
            elif right_qualifies:
                self.stage = "right_crunch"
                self.active_side = "RIGHT"
        elif self.stage == "left_crunch":
            self.active_side = "LEFT"
            if comp_left >= self.CRUNCH_EXIT_COMPRESSION and knee_lift_left <= self.KNEE_LIFT_EXIT:
                self.stage = "standing"
                self.reps += 1
                self.active_side = "NONE"
        elif self.stage == "right_crunch":
            self.active_side = "RIGHT"
            if comp_right >= self.CRUNCH_EXIT_COMPRESSION and knee_lift_right <= self.KNEE_LIFT_EXIT:
                self.stage = "standing"
                self.reps += 1
                self.active_side = "NONE"

        return {
            "reps": self.reps,
            "left_compression": round(float(comp_left), 2),
            "right_compression": round(float(comp_right), 2),
            "active_side": self.active_side,
            "knee_status": knee_status,
            "compression_status": compression_status,
            "torso_status": torso_status,
            "lateral_flexion": int(round(lateral_flexion_deg)),
            "stage": self.stage,
        }
