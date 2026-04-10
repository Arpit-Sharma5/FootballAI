# ⚽ Football AI — Video Analysis using Deep Learning

An AI-powered system that analyzes football match videos to detect players, track movements, assign teams, compute ball possession, and calculate real-time speed & distance — all rendered as an annotated output video.

![Screenshot](output_videos/screenshot.png)

## 🔍 What It Does

This project takes a raw football match video as input and produces a fully annotated video with:

- **Player & Referee Detection** — Uses a fine-tuned YOLOv5 model to detect every player, referee, and the ball in each frame.
- **Multi-Object Tracking** — ByteTrack assigns unique IDs to each detected object and maintains identity across frames.
- **Team Assignment** — K-Means clustering on jersey colors automatically classifies players into two teams.
- **Ball Possession Tracking** — Determines which player (and team) has the ball, and displays cumulative possession percentages.
- **Camera Movement Estimation** — Optical flow compensates for camera panning to isolate actual player movement.
- **Perspective Transformation** — Converts pixel coordinates into real-world meters using a homography matrix.
- **Speed & Distance Calculation** — Displays each player's speed (km/h) and total distance covered (meters) in real time.

## 🧠 Tech Stack

| Technology | Purpose |
|---|---|
| YOLOv5 (Ultralytics) | Object detection |
| ByteTrack (Supervision) | Multi-object tracking |
| K-Means (Scikit-learn) | Jersey color clustering |
| OpenCV | Optical flow, perspective transform, video I/O |
| NumPy & Pandas | Data processing & interpolation |
| PyTorch | Deep learning backend |
| Flask | Web application frontend |

## 📁 Project Structure

```

## 🚀 Run Locally (Full Pipeline)

Install the full ML/CV stack and run Flask locally:

```bash
python -m pip install -r requirements-local.txt
python app.py
```

Open: `http://localhost:8000`

## ☁️ Deploy Backend on Render

This repo includes `render.yaml` and `Procfile` for Render deployment.

1. Push this repository to GitHub.
2. In Render, create a new Web Service from this repository.
3. Render auto-detects `render.yaml` and uses:
	- Build command: `pip install -r requirements-local.txt`
	- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 1200`
4. Set environment variables in Render:
	- `ALLOWED_ORIGINS=https://footballai-nu.vercel.app`
	- `PUBLIC_API_BASE_URL=` (leave empty on backend service)
5. Deploy and copy your Render service URL, e.g. `https://footballai-backend.onrender.com`.

Health check endpoint:

`GET /api/health`

## 🌐 Connect Vercel Frontend to Render Backend

In your Vercel project, set:

- `PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com`

Then redeploy Vercel.

The frontend will send `/api/*` requests to Render while still serving UI from Vercel.
football_analysis-main/
├── main.py                         # Terminal-based pipeline
├── app.py                          # Flask web app
├── processing.py                   # Async processing wrapper
├── models/best.pt                  # Trained YOLOv5 weights
├── trackers/                       # Object detection & tracking
├── team_assigner/                  # Jersey color-based team classification
├── player_ball_assigner/           # Ball-to-player assignment
├── camera_movement_estimator/      # Optical flow camera compensation
├── view_transformer/               # Perspective transformation
├── speed_and_distance_estimator/   # Speed & distance computation
├── utils/                          # Video I/O & bbox utilities
├── stubs/                          # Pre-computed tracking data
├── templates/                      # Frontend HTML
└── static/                         # CSS & JavaScript
```