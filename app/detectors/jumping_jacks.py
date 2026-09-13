import math
from core.base_exercise import BaseExercise


class JumpingJackDetector(BaseExercise):
    ARM_OPEN_THRESHOLD = 130.0     # degrees (arms raised overhead/high)
    ARM_CLOSED_THRESHOLD = 70.0    # degrees (arms down by sides)
    STANCE_OPEN_THRESHOLD = 1.4    # ratio of ankle distance to shoulder width
    STANCE_CLOSED_THRESHOLD = 1.15 # ratio of ankle distance to shoulder width
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()
        self.stage = "closed"

    def reset(self) -> None:
        self.reps = 0
        self.stage = "closed"

    def process(self, landmarks) -> dict:
        key_indices = [
            self.LEFT_SHOULDER, self.RIGHT_SHOULDER,
            self.LEFT_HIP, self.RIGHT_HIP,
            self.LEFT_WRIST, self.RIGHT_WRIST,
            self.LEFT_ANKLE, self.RIGHT_ANKLE,
        ]

        # Ensure all key landmarks are sufficiently visible
        for idx in key_indices:
            if idx >= len(landmarks) or landmarks[idx].visibility < self.MIN_VISIBILITY:
                return {
                    "reps": self.reps,
                    "arm_angle": 0,
                    "stance_ratio": 0.0,
                    "arm_status": "N/A",
                    "stance_status": "N/A",
                    "sync_status": "N/A",
                    "stage": self.stage or "closed",
                }

        left_shoulder = self.get_point(landmarks, self.LEFT_SHOULDER)
        right_shoulder = self.get_point(landmarks, self.RIGHT_SHOULDER)
        left_hip = self.get_point(landmarks, self.LEFT_HIP)
        right_hip = self.get_point(landmarks, self.RIGHT_HIP)
        left_wrist = self.get_point(landmarks, self.LEFT_WRIST)
        right_wrist = self.get_point(landmarks, self.RIGHT_WRIST)
        left_ankle = self.get_point(landmarks, self.LEFT_ANKLE)
        right_ankle = self.get_point(landmarks, self.RIGHT_ANKLE)

        # 1. Arm abduction angles (Hip - Shoulder - Wrist)
        left_arm_angle = self.calculate_angle(left_hip, left_shoulder, left_wrist)
        right_arm_angle = self.calculate_angle(right_hip, right_shoulder, right_wrist)
        avg_arm_angle = (left_arm_angle + right_arm_angle) / 2.0

        # 2. Stance width normalized by shoulder width
        shoulder_width = math.sqrt(
            (left_shoulder[0] - right_shoulder[0]) ** 2 + (left_shoulder[1] - right_shoulder[1]) ** 2
        )
        ankle_distance = math.sqrt(
            (left_ankle[0] - right_ankle[0]) ** 2 + (left_ankle[1] - right_ankle[1]) ** 2
        )
        stance_ratio = ankle_distance / max(shoulder_width, 0.05)

        # 3. Derive status categories
        if avg_arm_angle >= self.ARM_OPEN_THRESHOLD:
            arm_status = "OVERHEAD"
        elif avg_arm_angle >= 80.0:
            arm_status = "MID-LEVEL"
        else:
            arm_status = "LOW"

        if stance_ratio >= self.STANCE_OPEN_THRESHOLD:
            stance_status = "WIDE"
        elif stance_ratio >= self.STANCE_CLOSED_THRESHOLD:
            stance_status = "MODERATE"
        else:
            stance_status = "NARROW"

        if abs(left_arm_angle - right_arm_angle) > 35.0:
            sync_status = "ARMS ASYMMETRIC"
        elif arm_status == "OVERHEAD" and stance_status == "NARROW":
            sync_status = "ARMS ONLY"
        elif arm_status == "LOW" and stance_status == "WIDE":
            sync_status = "LEGS ONLY"
        else:
            sync_status = "IN SYNC"

        # 4. State machine with hysteresis
        is_open = (avg_arm_angle >= self.ARM_OPEN_THRESHOLD) and (stance_ratio >= self.STANCE_OPEN_THRESHOLD)
        is_closed = (avg_arm_angle <= self.ARM_CLOSED_THRESHOLD) and (stance_ratio <= self.STANCE_CLOSED_THRESHOLD)

        if is_open:
            self.stage = "open"
        elif is_closed and self.stage == "open":
            self.stage = "closed"
            self.reps += 1
        elif is_closed and self.stage is None:
            self.stage = "closed"

        return {
            "reps": self.reps,
            "arm_angle": int(avg_arm_angle),
            "stance_ratio": round(float(stance_ratio), 1),
            "arm_status": arm_status,
            "stance_status": stance_status,
            "sync_status": sync_status,
            "stage": self.stage or "closed",
        }
