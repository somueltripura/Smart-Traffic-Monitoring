# Smart AI-Based Real-Time Traffic Monitoring System

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Inference Engine](https://img.shields.io/badge/AI%20Inference-YOLOv8%20ONNX-00BFFF.svg)](https://onnxruntime.ai/)
[![Computer Vision](https://img.shields.io/badge/Computer%20Vision-OpenCV%20%7C%20NumPy-00D9A6.svg)](https://opencv.org/)
[![Backend](https://img.shields.io/badge/Backend-Flask%20REST%20%7C%20SSE-FFB020.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Storage-SQLite%20WAL-FF3B4A.svg)](https://sqlite.org/)

A complete, production-ready AI-powered Traffic Monitoring System designed to monitor road traffic using live camera feeds (RTSP/Webcam) or uploaded video files. The system performs real-time vehicle detection, multi-object tracking, directional vehicle counting, region-of-interest (ROI) density analysis, calibrated speed estimation, and intelligent congestion classification — presented through a futuristic dark control center web dashboard.

> 🌐 **Dashboard Host URL:** [`http://localhost:5000`](http://localhost:5000) &nbsp;|&nbsp; 🩺 **Health Check:** [`http://localhost:5000/api/health`](http://localhost:5000/api/health)

---

## Table of Contents
1. [Key Capabilities](#1-key-capabilities)
2. [Technology Stack](#2-technology-stack)
3. [Core Mathematical & Algorithmic Modules](#3-core-mathematical--algorithmic-modules)
4. [Project Directory Layout](#4-project-directory-layout)
5. [Installation & Quickstart](#5-installation--quickstart)
6. [REST API Reference](#6-rest-api-reference)
7. [Camera Calibration & Geometry Manual](#7-camera-calibration--geometry-manual)
8. [Dashboard UI/UX Walkthrough](#8-dashboard-uiux-walkthrough)
9. [Automated Testing Suite](#9-automated-testing-suite)
10. [Performance Optimization & Troubleshooting](#10-performance-optimization--troubleshooting)

---

## 1. Key Capabilities

- **Real-Time Vehicle Detection:** Accelerated YOLOv8 inference running natively on ONNX Runtime (`yolov8.onnx`).
- **Vehicle Classification:** Filters specifically for target road categories:
  - 🚗 **Cars** (COCO Class 2)
  - 🏍️ **Motorcycles** (COCO Class 3)
  - 🚌 **Buses** (COCO Class 5)
  - 🚚 **Trucks** (COCO Class 7)
- **Multi-Object Tracking (ByteTrack):** Assigns persistent IDs, maintains trajectories, and recovers vehicles across temporary occlusions.
- **Directional Virtual Line Counting:** Non-intrusive counting barrier calculating `Inbound` vs. `Outbound` traffic without duplicate counting.
- **Traffic Density Analysis:** Spatial containment within arbitrary road polygons with documented road capacity ratio metrics.
- **Calibrated Speed Estimation:** 4-point perspective homography or linear metric scaling. Strictly indicates `Unavailable / Uncalibrated` if reference markers are unconfigured.
- **Intelligent Congestion Detection:** Multi-variable score evaluating vehicle concentration, average speed, and stationary queue ratios.
- **Decoupled Architecture:** Asynchronous background worker (`StreamWorker`) ensuring the Flask HTTP server and web dashboard never block during inference.
- **Live Video Streaming & Telemetry:** Low-latency multipart MJPEG streaming (`/api/stream/video`) paired with Server-Sent Events (`/api/stream/events`) at 2 Hz.

---

## 2. Technology Stack

- **Computer Vision & AI:** Python 3.11+, OpenCV 4.x, NumPy, YOLOv8 (ONNX Runtime engine)
- **Tracking:** Kalman Filter state prediction with two-stage IoU association (ByteTrack methodology)
- **Backend Framework:** Flask 3.x, Flask-CORS, Werkzeug
- **Storage Layer:** SQLite3 with WAL (Write-Ahead Logging) for multi-thread concurrent safety
- **Frontend Technologies:** HTML5, CSS3, JavaScript (Vanilla ES6+), Chart.js 4.x, Leaflet.js

---

## 3. Core Mathematical & Algorithmic Modules

### A. Virtual Line Intersection & Directional Counting
The virtual counting line segment is defined by $P_1(x_1, y_1)$ and $P_2(x_2, y_2)$. When a tracked vehicle moves from previous centroid $C_{t-1}$ to current centroid $C_t$, intersection is computed via the 2D cross-product:
$$\text{CCW}(A, B, C) = (B_x - A_x)(C_y - A_y) - (B_y - A_y)(C_x - A_x)$$

An intersection occurs if:
$$(\text{CCW}(P_1, P_2, C_{t-1}) \cdot \text{CCW}(P_1, P_2, C_t) < 0) \land (\text{CCW}(C_{t-1}, C_t, P_1) \cdot \text{CCW}(C_{t-1}, C_t, P_2) < 0)$$

The normal vector $\vec{n} = (-(P_{2y} - P_{1y}), P_{2x} - P_{1x})$ and displacement vector $\vec{v} = C_t - C_{t-1}$ yield the direction:
$$\text{Direction} = \begin{cases} \text{Inbound}, & \text{if } \vec{v} \cdot \vec{n} > 0 \\ \text{Outbound}, & \text{otherwise} \end{cases}$$

### B. Documented Traffic Density Calculation
Density percentage is computed as the ratio of vehicles detected inside the defined road polygon $\mathcal{P}_{ROI}$ to the safe road segment capacity $C_{\max}$:
$$\text{Density (\%)} = \min\left(100.0, \frac{N_{\text{vehicles in ROI}}}{C_{\max}} \times 100.0\right)$$
- **Low:** $0\% \le \text{Density} < 35\%$
- **Medium:** $35\% \le \text{Density} < 70\%$
- **High:** $\text{Density} \ge 70\%$ (Congestion Alert triggered)

### C. Calibrated Speed Estimation (Homography)
A perspective transformation matrix $\mathbf{H} \in \mathbb{R}^{3 \times 3}$ maps the 4 quadrilateral road perspective points on the camera plane to an overhead metric rectangle in meters:
$$\begin{bmatrix} X' \\ Y' \\ W' \end{bmatrix} = \mathbf{H} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}, \quad X = \frac{X'}{W'}, \quad Y = \frac{Y'}{W'}$$

Real ground displacement $\Delta D = \sqrt{(X_t - X_{t-k})^2 + (Y_t - Y_{t-k})^2}$ meters over elapsed time $\Delta t = \frac{k}{\text{FPS}}$ seconds produces calibrated speed in km/h:
$$V_{\text{km/h}} = \left(\frac{\Delta D}{\Delta t}\right) \times 3.6$$

---

## 4. Project Directory Layout

```
smart-traffic-monitoring/
│
├── backend/
│   ├── app.py                      # Flask application factory & static server
│   ├── config.py                   # Centralized application configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py                  # Core REST endpoints (/api/traffic, /api/detection/*)
│   │   ├── cameras.py              # Camera CRUD and geometry reconfiguration
│   │   ├── stream.py               # MJPEG video and SSE telemetry streams
│   │   └── analytics.py            # Historical trends and volume statistics
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stream_worker.py        # Dedicated background video ingestion & inference
│   │   └── db_service.py           # SQLite persistence & query aggregations
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── detector.py             # YOLOv8 ONNX Runtime inference wrapper
│   │   ├── tracker.py              # Multi-object ByteTrack tracker
│   │   ├── counter.py              # Virtual line crossing & deduplication
│   │   ├── density.py              # Road polygon ROI density analyzer
│   │   └── speed.py                # Homography calibration & speed estimator
│   ├── models/
│   │   ├── __init__.py
│   │   └── entities.py             # Domain data models (Camera, Detection, Stats, etc.)
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py                   # Thread-safe SQLite connection & schema initialization
│   └── utils/
│       ├── __init__.py
│       ├── drawing.py              # HUD overlays, bounding boxes & ROI drawing
│       ├── logger.py               # Centralized rotating file & console logger
│       ├── validators.py           # Input, file, and coordinate validators
│       └── generate_sample_video.py# Test video generation script
│
├── frontend/
│   ├── index.html                  # Futuristic dark control center dashboard
│   ├── css/
│   │   └── style.css               # Sci-Fi dark theme styling (#07111F, #00BFFF)
│   ├── js/
│   │   ├── app.js                  # Main UI controller & SSE consumer
│   │   ├── api.js                  # Fetch REST API client
│   │   ├── charts.js               # Chart.js flow & category charts
│   │   ├── gauges.js               # Custom Canvas density & speed gauges
│   │   └── map.js                  # Leaflet.js interactive GIS camera map
│   └── assets/
│       └── logo.svg                # Vector brand logo
│
├── models/
│   ├── yolov8.onnx                 # Pretrained YOLOv8 vehicle detection model
│   └── yolov8n.onnx
├── uploads/
│   └── demo_traffic.mp4            # Sample traffic video clip
├── logs/
│   └── traffic_system.log          # Rotating application logs
├── tests/
│   ├── test_detection.py           # YOLOv8 inference tests
│   ├── test_tracker.py             # Tracking & occlusion tests
│   ├── test_counter.py             # Line intersection & deduplication tests
│   ├── test_density.py             # ROI density & capacity tests
│   ├── test_speed.py               # Speed calibration tests
│   └── test_api.py                 # Flask REST endpoints integration tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Installation & Quickstart

### Prerequisites
- Python 3.11 or higher
- Git

### Step 1: Clone and Enter Directory
```bash
git clone https://github.com/your-username/smart-traffic-monitoring.git
cd smart-traffic-monitoring
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application Server
```bash
python backend/app.py
```

### Step 5: Open the Web Dashboard
Navigate to your browser:
```
http://localhost:5000
```
Click **"START MONITORING"** on the dashboard. The system will immediately begin processing the included demo traffic video (`demo_traffic.mp4`), drawing real-time bounding boxes, counting crossing vehicles, updating gauges, and streaming live metrics!

---

## 5.1 Docker Deployment (Single Command)

You can build and deploy the entire system in isolated Docker containers:

### Option A: Using Docker Compose (Recommended)
```bash
docker compose up -d --build
```
This automatically builds the image, starts the container in the background, maps port `5000:5000`, and sets up persistent host volume mounts for `uploads/`, `logs/`, and `backend/database/`.

### Host Links & Service Access URLs

Once the container is started, access the application and endpoints via:

| Service / Endpoint | Host Link / URL | Description |
| :--- | :--- | :--- |
| 🖥️ **Control Dashboard** | [`http://localhost:5000`](http://localhost:5000) | Futuristic web control center & live video dashboard |
| 🌐 **LAN / Network Access** | `http://<HOST_IP>:5000` | Access from other devices/monitors on the local network |
| 🩺 **System Health Check** | [`http://localhost:5000/api/health`](http://localhost:5000/api/health) | Container health, ONNX model status, and worker state |
| 🎥 **Live MJPEG Stream** | [`http://localhost:5000/api/stream/video`](http://localhost:5000/api/stream/video) | Real-time processed video feed with HUD overlays |
| ⚡ **SSE Live Telemetry** | [`http://localhost:5000/api/stream/events`](http://localhost:5000/api/stream/events) | 2 Hz Server-Sent Events live metrics stream |

To view container logs:
```bash
docker compose logs -f
```

To stop the container:
```bash
docker compose down
```

### Option B: Using Plain Docker CLI
```bash
# 1. Build the Docker Image
docker build -t smart-traffic-monitoring .

# 2. Run the Container
docker run -d \
  --name smart_traffic_server \
  -p 5000:5000 \
  -v ${PWD}/uploads:/app/uploads \
  -v ${PWD}/logs:/app/logs \
  -v ${PWD}/backend/database:/app/backend/database \
  smart-traffic-monitoring
```

---

## 6. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health check, AI model status, and worker state. |
| `GET` | `/api/traffic` | Consolidated real-time telemetry (counts, density, speed, congestion). |
| `GET` | `/api/traffic/counts` | Vehicle counts breakdown (cars, buses, trucks, motorcycles, total). |
| `GET` | `/api/traffic/density` | Density percentage, level classification (Low/Med/High), and alert state. |
| `GET` | `/api/traffic/speed` | Average speed in km/h or uncalibrated movement indicator. |
| `GET` | `/api/traffic/congestion`| Congestion classification (Normal, Moderate, High Congestion). |
| `GET` | `/api/cameras` | List of all registered camera sources and streaming statuses. |
| `POST` | `/api/cameras` | Register a new camera node (webcam index, video file, or RTSP URL). |
| `POST` | `/api/cameras/<id>/configure` | Dynamically update counting line, ROI polygon, or speed calibration. |
| `POST` | `/api/detection/start` | Start monitoring for a specific camera or custom video source. |
| `POST` | `/api/detection/stop` | Stop the active background video processing worker. |
| `POST` | `/api/upload` | Upload a new traffic video file (`.mp4`, `.avi`, `.mov`, `.mkv`). |
| `GET` | `/api/stream/video` | Multipart MJPEG real-time video stream for HTML `<img>` tag. |
| `GET` | `/api/stream/events` | Server-Sent Events (SSE) telemetry broadcast stream at 2 Hz. |
| `GET` | `/api/analytics` | Aggregated traffic volume metrics, hourly distributions, and trends. |
| `GET` | `/api/history` | Historical time-series traffic records (query param `?limit=50`). |

---

## 7. Camera Calibration & Geometry Manual

To customize virtual counting lines and perspective calibration for any custom camera or video angle:

1. Click the **"CALIBRATION & ROI"** button in the dashboard toolbar.
2. **Road Safe Capacity:** Set the maximum number of vehicles safely fitting within the road segment (e.g., `15`).
3. **Virtual Counting Line:** Define the two endpoints of the counting line:
   ```json
   [[100, 480], [1180, 480]]
   ```
4. **ROI Density Polygon:** Specify 3 or more vertices defining the road quadrilateral:
   ```json
   [[120, 280], [1160, 280], [1240, 680], [40, 680]]
   ```
5. **Speed Metric Scale:** Configure the ground distance ratio in meters per pixel (e.g., `0.05` means 1 pixel = 5 centimeters).
6. Click **"Save Configuration"**. The background processing worker updates the geometry in real time without restarting.

---

## 8. Dashboard UI/UX Walkthrough

The dashboard implements a **Futuristic Dark Control Center** aesthetic with a `#07111F` dark background, `#102238` card panels, and `#00BFFF` / `#00D9A6` neon telemetry accents:

- **Top HUD:** Displays live AI engine status (ONNX Runtime), real-time processing FPS, and cumulative vehicle counters.
- **Video Monitor:** Live video feed rendering corner-bracket bounding boxes, vehicle class badges, confidence scores, trailing trajectories, virtual counting barrier, and semi-transparent road ROI polygon.
- **KPI Stat Cards:** Dedicated visual cards tracking Cars, Buses, Trucks, Motorcycles, and Total Vehicles with directional breakdowns.
- **Dual Telemetry Gauges:** Custom animated HTML5 canvas gauges displaying Traffic Density percentage and Average Speed.
- **Congestion Alert Card:** Transitions dynamically between Green (Normal), Amber (Moderate), and Glowing Red (High Congestion).
- **Traffic Flow Chart:** Real-time Chart.js stream visualizing vehicle arrivals over time.
- **Interactive GIS Map:** Leaflet.js dark map displaying all camera nodes with interactive status popups and one-click camera switching.

---

## 9. Automated Testing Suite

The repository includes a comprehensive unit and integration test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Verified Test Suites:
- `tests/test_detection.py`: Validates YOLOv8 ONNX loading, warmup, empty/black frame handling, and class filtering.
- `tests/test_tracker.py`: Verifies IoU state association and track ID preservation across temporary occlusions.
- `tests/test_counter.py`: Tests geometric 2D line segment intersection, directional classification, and duplicate counting prevention.
- `tests/test_density.py`: Tests polygon containment, capacity ratio math, and congestion alert triggers.
- `tests/test_speed.py`: Tests speed calculation under uncalibrated mode (unavailable) and calibrated mode (km/h).
- `tests/test_api.py`: Tests all Flask REST endpoints, upload validation, camera CRUD, and error handlers.

---

## 10. Performance Optimization & Troubleshooting

- **Threading Concurrency:** Video capture and ONNX inference run exclusively in a background worker thread (`StreamWorker`), completely decoupling heavy computer vision workloads from Flask web requests.
- **Frame Skipping:** For low-power CPUs or high-resolution 4K streams, adjust `FRAME_SKIP=2` or `FRAME_SKIP=3` in `.env` to process every $N^{\text{th}}$ frame while maintaining tracking smoothness.
- **SQLite Concurrency:** SQLite is initialized with `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;` ensuring non-blocking reads and concurrent analytics queries during video writes.
- **Memory Management:** OpenCV video captures and frame buffers are clamped to single-item ring buffers to prevent memory growth during long-running streams.
