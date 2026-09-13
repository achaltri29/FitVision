import math
from core.base_exercise import BaseExercise


class HighKneesDetector(BaseExercise):
    """
    Detector for High Knees exercise.
    One repetition is defined as ONE completed knee lift:
    - Left knee elevated above threshold and returned to ground = 1 rep.
    - Right knee elevated above threshold and returned to ground = 1 rep.
    - Alternating sequence (Left -> Right) = 2 reps.
    """
    KNEE_HIGH_THRESHOLD = -0.10   # normalized knee elevation relative to hip (y increases downward)
    KNEE_LOW_THRESHOLD = -0.45    # normalized return threshold toward standing
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()
        self.left_stage = "ground"
        self.right_stage = "ground"
        self.active_leg = "NONE"
        self.stage = "ground"

    def reset(self) -> None:
        self.reps = 0
        self.left_stage = "ground"
        self.right_stage = "ground"
        self.active_leg = "NONE"
        self.stage = "ground"

    def process(self, landmarks) -> dict:
        key_indices = [
            self.LEFT_SHOULDER, self.RIGHT_SHOULDER,
            self.LEFT_HIP, self.RIGHT_HIP,
            self.LEFT_KNEE, self.RIGHT_KNEE,
            self.LEFT_ANKLE, self.RIGHT_ANKLE,
        ]

        # 1. Ensure all key landmarks are visible
        for idx in key_indices:
            if idx >= len(landmarks) or landmarks[idx].visibility < self.MIN_VISIBILITY:
                return {
                    "reps": self.reps,
                    "knee_height": 0,
                    "torso_lean_angle": 0,
                    "knee_status": "N/A",
                    "active_leg": self.active_leg,
                    "torso_status": "N/A",
                    "stage": self.stage,
                }

        # 2. Extract 2D and 3D positions
        left_shoulder = landmarks[self.LEFT_SHOULDER]
        right_shoulder = landmarks[self.RIGHT_SHOULDER]
        left_hip = landmarks[self.LEFT_HIP]
        right_hip = landmarks[self.RIGHT_HIP]
        left_knee = landmarks[self.LEFT_KNEE]
        right_knee = landmarks[self.RIGHT_KNEE]

        # 3. Scale-invariant reference: torso height
        shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2.0
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2.0
        shoulder_mid_z = (left_shoulder.z + right_shoulder.z) / 2.0

        hip_mid_x = (left_hip.x + right_hip.x) / 2.0
        hip_mid_y = (left_hip.y + right_hip.y) / 2.0
        hip_mid_z = (left_hip.z + right_hip.z) / 2.0

        torso_height = max(abs(hip_mid_y - shoulder_mid_y), 0.10)

        # 4. Normalized vertical knee lift (higher is higher up, 0.0 is hip level)
        left_knee_lift = (left_hip.y - left_knee.y) / torso_height
        right_knee_lift = (right_hip.y - right_knee.y) / torso_height

        # 5. Torso lean computation
        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y  # negative
        dz = shoulder_mid_z - hip_mid_z  # positive when shoulders move backward relative to hips
        torso_len = max(abs(dy), 1e-5)

        backward_lean_deg = math.degrees(math.atan2(dz, torso_len))
        total_lean_deg = int(round(math.degrees(math.atan2(math.sqrt(dx**2 + max(0.0, dz)**2), torso_len))))

        if backward_lean_deg >= 15.0:
            torso_status = "LEANING BACK"
        elif total_lean_deg > 20:
            torso_status = "LEANING"
        else:
            torso_status = "UPRIGHT"

        # 6. Active leg determination & knee status
        if left_knee_lift >= self.KNEE_HIGH_THRESHOLD or right_knee_lift >= self.KNEE_HIGH_THRESHOLD:
            knee_status = "HIGH"
            if left_knee_lift >= right_knee_lift:
                self.active_leg = "LEFT"
            else:
                self.active_leg = "RIGHT"
        elif left_knee_lift >= -0.35 or right_knee_lift >= -0.35:
            knee_status = "LOW"
            if left_knee_lift >= right_knee_lift:
                self.active_leg = "LEFT"
            else:
                self.active_leg = "RIGHT"
        else:
            knee_status = "GROUND"
            self.active_leg = "NONE"

        # 7. Independent per-leg state machine with hysteresis
        # Left leg
        if left_knee_lift >= self.KNEE_HIGH_THRESHOLD:
            if self.left_stage != "up":
                self.left_stage = "up"
        elif left_knee_lift <= self.KNEE_LOW_THRESHOLD:
            if self.left_stage == "up":
                self.left_stage = "ground"
                self.reps += 1

        # Right leg
        if right_knee_lift >= self.KNEE_HIGH_THRESHOLD:
            if self.right_stage != "up":
                self.right_stage = "up"
        elif right_knee_lift <= self.KNEE_LOW_THRESHOLD:
            if self.right_stage == "up":
                self.right_stage = "ground"
                self.reps += 1

        # Update composite stage for display
        if self.left_stage == "up":
            self.stage = "left_up"
        elif self.right_stage == "up":
            self.stage = "right_up"
        else:
            self.stage = "ground"

        # Active knee height index (normalized * 100 for display, e.g. 95)
        active_lift = max(left_knee_lift, right_knee_lift)
        knee_height_val = int(round((active_lift + 1.0) * 100))

        return {
            "reps": self.reps,
            "knee_height": knee_height_val,
            "torso_lean_angle": total_lean_deg,
            "knee_status": knee_status,
            "active_leg": self.active_leg,
            "torso_status": torso_status,
            "stage": self.stage,
        }
