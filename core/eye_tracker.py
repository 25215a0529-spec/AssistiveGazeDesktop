import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions import face_mesh as mp_face_mesh

class DualModalityEyeTracker:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.prev_x = None
        self.prev_y = None
        self.alpha = 0.26  # Balanced between stability and immediate response

        # Neutral eye center baseline
        self.calib_x = 0.0
        self.calib_y = 0.0
        self.calib_samples = []
        self.calibrated = False

        # Tuned amplification gains for pure eyeball rotation (no neck movement)
        self.gain_x = 15.0
        self.gain_y = 18.0

    def recalibrate(self):
        """Resets the baseline so looking at screen center re-zeros the cursor."""
        self.calib_samples.clear()
        self.calibrated = False
        self.prev_x = None
        self.prev_y = None

    def process_frame(self, frame, screen_w, screen_h):
        try:
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            debug_frame = cv2.resize(frame, (180, 120))

            if not results.multi_face_landmarks:
                cv2.putText(debug_frame, "No Face", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                return None, debug_frame, True

            lms = results.multi_face_landmarks[0].landmark

            # ---------------- Right Eye (User's Right / Webcam Left) ----------------
            r_out = np.array([lms[33].x * w, lms[33].y * h])
            r_in = np.array([lms[133].x * w, lms[133].y * h])
            r_top = np.array([lms[159].x * w, lms[159].y * h])
            r_bot = np.array([lms[145].x * w, lms[145].y * h])
            r_iris = np.array([lms[468].x * w, lms[468].y * h])

            # ---------------- Left Eye (User's Left / Webcam Right) ----------------
            l_in = np.array([lms[362].x * w, lms[362].y * h])
            l_out = np.array([lms[263].x * w, lms[263].y * h])
            l_top = np.array([lms[386].x * w, lms[386].y * h])
            l_bot = np.array([lms[374].x * w, lms[374].y * h])
            l_iris = np.array([lms[473].x * w, lms[473].y * h])

            r_width = np.linalg.norm(r_out - r_in)
            l_width = np.linalg.norm(l_out - l_in)

            if r_width < 8 or l_width < 8:
                return None, debug_frame, True

            # Blink Detection via Eye Aspect Ratio
            r_ear = np.linalg.norm(r_top - r_bot) / r_width
            l_ear = np.linalg.norm(l_top - l_bot) / l_width
            ear = (r_ear + l_ear) / 2.0

            # Discard frame if eyelids close (natural blink)
            if ear < 0.12:
                cv2.putText(debug_frame, "Blink", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                if self.prev_x is not None:
                    return (int(self.prev_x), int(self.prev_y)), debug_frame, True
                return None, debug_frame, True

            # Socket geometric centers
            r_center = (r_out + r_in) / 2.0
            l_center = (l_out + l_in) / 2.0

            # Normalized pupil displacement vector relative to socket width
            r_dx = (r_iris[0] - r_center[0]) / r_width
            l_dx = (l_iris[0] - l_center[0]) / l_width
            pupil_dx = (r_dx + l_dx) / 2.0

            r_dy = (r_iris[1] - r_center[1]) / r_width
            l_dy = (l_iris[1] - l_center[1]) / l_width
            pupil_dy = (r_dy + l_dy) / 2.0

            # ---------------- 20-FRAME AUTO-CENTERING ----------------
            if not self.calibrated:
                self.calib_samples.append((pupil_dx, pupil_dy))
                cv2.putText(debug_frame, f"Calibrating {len(self.calib_samples)}/20", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
                if len(self.calib_samples) >= 20:
                    self.calib_x = float(np.median([s[0] for s in self.calib_samples]))
                    self.calib_y = float(np.median([s[1] for s in self.calib_samples]))
                    self.calibrated = True
                return (int(screen_w / 2), int(screen_h / 2)), debug_frame, False

            # Deviation from neutral center
            delta_x = pupil_dx - self.calib_x
            delta_y = pupil_dy - self.calib_y

            # Correct screen coordinate mapping
            # Looking right in real life moves webcam iris left -> delta_x is negative -> norm_x increases
            norm_x = 0.5 - (delta_x * self.gain_x)
            norm_y = 0.5 + (delta_y * self.gain_y)

            # Keep cursor comfortably within actionable screen limits
            raw_x = np.clip(norm_x, 0.05, 0.95) * screen_w
            raw_y = np.clip(norm_y, 0.06, 0.94) * screen_h

            # Adaptive smoothing: filters micro-tremors during fixation
            if self.prev_x is None:
                smooth_x, smooth_y = raw_x, raw_y
            else:
                dist = np.hypot(raw_x - self.prev_x, raw_y - self.prev_y)
                # Tight deadzone when holding gaze over a card
                if dist < 20.0:
                    a = 0.10
                elif dist < 80.0:
                    a = 0.26
                else:
                    a = 0.48

                smooth_x = a * raw_x + (1.0 - a) * self.prev_x
                smooth_y = a * raw_y + (1.0 - a) * self.prev_y

            self.prev_x, self.prev_y = smooth_x, smooth_y

            cv2.putText(debug_frame, "Active", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            return (int(smooth_x), int(smooth_y)), debug_frame, False

        except Exception as e:
            print(f"Tracking error: {e}")
            return None, None, True