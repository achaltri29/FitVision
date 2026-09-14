# FitVision — AI Gym Coach

FitVision is an intelligent, real-time workout assistant that leverages computer vision and proactive artificial intelligence to evaluate exercise biomechanics, count repetitions, and deliver high-energy voice coaching through your web browser.

---

## Live Demo

- **Streamlit Application**: [https://fitvision-realtime-ai-coach.streamlit.app/](https://fitvision-realtime-ai-coach.streamlit.app/)
- **Product Landing Page**: [https://fitvision-landing.onrender.com/](https://fitvision-landing.onrender.com/)

---

## Features

### Supported Exercises & Biomechanical Tracking
FitVision implements state-machine-driven kinematic detectors for 8 distinct compound and bodyweight exercises:

- **Squats**: Measures hip depth, knee flexion angles, and forward torso incline; classifies depth (*Good Depth*, *Parallel*, *Too Shallow*) and monitors back posture.
- **Push-ups**: Tracks elbow angles, plank body alignment (shoulder–hip–ankle collinearity), and detects hip sagging or excessive elevation.
- **Biceps Curls (Dumbbell)**: Evaluates elbow flexion/extension, isolates upper-arm displacement to enforce shoulder stability, and flags torso momentum/swinging.
- **Shoulder Press**: Tracks overhead pressing trajectories, elbow lockout extension, and excessive lumbar hyperextension (back arching).
- **Lunges**: Monitors lead knee angle, upright torso alignment, and bilateral stability.
- **Jumping Jacks**: Computes arm abduction angles and stance width ratios (ankle spread normalized to shoulder breadth) to verify movement range and rhythm.
- **High Knees**: Analyzes alternating knee elevation relative to the hip line, running cadence, and vertical torso lean.
- **Standing Oblique Crunches**: Detects active-side lateral knee drive toward the elbow, assesses torso lateral flexion, and verifies return to center.

### Core Capabilities
- **Real-Time Landmark Tracking**: Streams live camera video via WebRTC, computing 33 3D skeletal landmarks at high frame rates using MediaPipe's full pose landmarker model.
- **Proactive AI Coaching**: Evaluates exercise milestones (`workout_started`, `halfway`, `last_rep`, `set_completed`, `form_alert`, `workout_completed`) and queries Groq's low-latency LLMs for concise, exercise-specific coaching cues.
- **Real-Time Voice Feedback**: Synthesizes motivational audio on the fly with Google Text-to-Speech (gTTS) and streams spoken guidance directly through the browser.
- **Session & Metric Tracking**: Displays live HUD telemetry (angles, posture status, active reps, target sets, elapsed time).
- **User Authentication & Persistent History**: Lightweight session-based login with SQLite persistence to track historic workout logs, completed sets, reps, and cumulative session durations.

---

## How It Works

```
[ Web Camera ]
       │
       ▼ (WebRTC PeerConnection)
[ streamlit-webrtc / PyAV Frame Ingestion ]
       │
       ▼ (RGB Video Stream)
[ MediaPipe PoseLandmarker (Full 33-point 3D Mesh) ]
       │
       ▼ (Kinematic Feature Extraction)
[ Biomechanical Angle & Vector Calculators ]
       │
       ▼ (Phase Transition & Threshold Evaluation)
[ Exercise State Detectors (Squat, Push-up, etc.) ]
       │
       ├───► [ Repetition Counter & HUD Telemetry Overlay ]
       │
       ▼ (State Change / Form Fault Event)
[ Event Pipeline & State Orchestrator ]
       │
       ▼ (Context-Engineered Prompt)
[ Groq Low-Latency LLM Inference ]
       │
       ▼ (Targeted Coaching Advice Text)
[ gTTS Voice Synthesis Engine ]
       │
       ▼ (Audio Data Stream)
[ In-Browser Audio Playback & SQLite Logging ]
```

---

## Tech Stack

| Domain | Technology / Library | Version | Description |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>=3.11` | Core backend and pipeline logic |
| **Frontend / App Framework** | Streamlit | `1.54.0` | Reactive application interface and HUD telemetry |
| **WebRTC Streaming** | streamlit-webrtc / PyAV | `0.64.5` / `17.1.0` | Browser-to-server video frame transmission |
| **Computer Vision** | MediaPipe | `0.10.14` | 33-point 3D pose landmark detection model |
| **Image Processing** | OpenCV Headless | `4.10.0.84` | Frame manipulation and visual skeleton overlay |
| **LLM Inference** | Groq Python SDK | `>=0.12.0` | Fast AI coaching generation |
| **Voice Synthesis** | gTTS | `2.5.3` | Text-to-speech audio cue generation |
| **Data & Serialization** | Pandas / Protobuf | `2.2.3` / `<5.0` | Tabular workout history and model data protocols |
| **Database** | SQLite3 | Built-in | User session profiles and historical exercise logs |
| **Landing Page** | HTML5 / CSS3 / Vanilla JS | — | Responsive showcase landing page |
| **Hosting (Landing)** | Render | Static Site | Automated static site deployment from Git |
| **Hosting (App)** | Streamlit Community Cloud | Container | Native cloud deployment with WebRTC camera access |

---

## Project Structure

```
FitVision/
├── app/
│   ├── core/
│   │   └── base_exercise.py          # Base abstract class for exercise detectors
│   ├── detectors/                     # Exercise-specific kinematic algorithms
│   │   ├── biceps_curl.py
│   │   ├── high_knees.py
│   │   ├── jumping_jacks.py
│   │   ├── lunges.py
│   │   ├── pushup.py
│   │   ├── shoulder_press.py
│   │   ├── squat.py
│   │   └── standing_oblique_crunches.py
│   ├── ml_models/
│   │   └── pose_landmarker_full.task  # Pretrained MediaPipe 33-landmark pose model (9 MB)
│   ├── services/
│   │   ├── auth/                      # Session authentication & login wall
│   │   ├── coaching/                  # LLM coach, TTS audio engine & voice pipeline
│   │   ├── config/                    # Workouts, connections & coaching system prompts
│   │   ├── persistence/               # SQLite database schemas and queries
│   │   ├── state/                     # Session state initialization defaults
│   │   ├── tracking/                  # Real-time metric synchronization
│   │   ├── ui/                        # CSS injection and WebRTC styling utilities
│   │   └── vision/                    # Video processor & skeleton renderer
│   ├── static/                        # App design system styles and custom fonts
│   ├── main.py                        # Streamlit application entry point
│   ├── packages.txt                   # Linux system dependencies for app container
│   └── requirements.txt               # App-specific Python dependencies
├── landing-page/
│   ├── fonts/                         # Web typography assets
│   ├── IMGs/                          # UI gallery preview captures
│   ├── videos/                        # FitVision Demo Video.mp4
│   ├── index.html                     # Showcase landing page markup
│   └── style.css                      # Landing page design system
├── packages.txt                       # Root Linux dependencies for Streamlit Cloud (libgl1)
├── pyproject.toml                     # Project packaging and dependency definitions
└── README.md                          # Project documentation
```

---

## Local Setup

### Prerequisites
- Python `3.11` or higher
- A webcam connected to your machine
- A [Groq API Key](https://console.groq.com/keys) for voice coaching

### 1. Clone the Repository
```bash
git clone https://github.com/achaltri29/FitVision.git
cd FitVision
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
# On Windows use: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r app/requirements.txt
```

*(Optional: If running on Linux without desktop GUI packages installed, ensure `libgl1` and `libglib2.0-0` are installed: `sudo apt-get install -y libgl1 libglib2.0-0`)*

### 4. Configure Environment Variables
Create an `.env` file inside the `app/` directory (or export the variable directly):

```bash
# app/.env
GROQ_API_KEY="your_groq_api_key_here"
```

> **Note**: Never commit your `.env` file to source control. It is protected by `.gitignore`.

### 5. Run the Streamlit Application
From the repository root, start the Streamlit server:
```bash
streamlit run app/main.py
```

The application will launch in your default browser at `http://localhost:8501`.

### 6. View the Landing Page Locally
To explore the static landing page locally, open `landing-page/index.html` in your browser or run a static file server:
```bash
python3 -m http.server 8000 --directory landing-page
```
Then visit `http://localhost:8000`.

---

## Deployment Architecture

FitVision is deployed across two independent services:

1. **Static Landing Page** (Render):
   - **Host**: Render Static Site
   - **Root Directory**: `landing-page`
   - **Publish Directory**: `.`
   - **Live URL**: [https://fitvision-landing.onrender.com/](https://fitvision-landing.onrender.com/)

2. **Streamlit Application** (Streamlit Community Cloud):
   - **Host**: Streamlit Community Cloud
   - **Main File Path**: `app/main.py`
   - **Python Runtime**: `3.11`
   - **System Libraries**: Handled by root `packages.txt` (`libgl1`, `libglib2.0-0`)
   - **Secrets Management**: `GROQ_API_KEY` configured in Streamlit Cloud Secrets
   - **HTTPS / WebRTC**: Handled natively by Streamlit Cloud with public STUN fallback
   - **Live URL**: [https://fitvision-realtime-ai-coach.streamlit.app/](https://fitvision-realtime-ai-coach.streamlit.app/)

---

## Security & Repository Hygiene

- **API Keys & Credentials**: The application queries `GROQ_API_KEY` via `os.environ` and `st.secrets`. All `.env` variations are explicitly ignored by `.gitignore`.
- **Database Isolation**: The SQLite `data.db` file is excluded from version control to prevent check-in of local session data.
- **Model Distribution**: The 9 MB MediaPipe task binary (`app/ml_models/pose_landmarker_full.task`) is intentionally tracked via Git to ensure zero external model download dependencies during cold boot.

---

## Potential Future Improvements

- **Additional Exercise Modules**: Expanding detector coverage to deadlifts, pull-ups, lateral raises, and barbell hip thrusts.
- **Temporal Consistency Smoothing**: Implementing Savitzky-Golay filtering on raw landmark trajectories to smooth high-frequency tracking jitter.
- **Cloud Database Synchronization**: Integrating managed PostgreSQL / Supabase for persistent cross-device workout tracking.
- **Adaptive Velocity Tracking**: Estimating barbell/limb velocity to monitor power output, tempo, and rate of fatigue across sets.
