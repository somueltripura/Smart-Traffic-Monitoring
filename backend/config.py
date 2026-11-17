import os
from pathlib import Path

# Resolve base directories
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MODELS_DIR = PROJECT_ROOT / "models"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
LOGS_DIR = PROJECT_ROOT / "logs"
DATABASE_DIR = BACKEND_DIR / "database"

# Ensure directories exist
for directory in [MODELS_DIR, UPLOADS_DIR, LOGS_DIR, DATABASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class Config:
    """Application Configuration Settings."""

    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-traffic-ai-security-key-2026")

    # Paths
    BASE_DIR = PROJECT_ROOT
    MODELS_DIR = MODELS_DIR
    UPLOADS_DIR = UPLOADS_DIR
    LOGS_DIR = LOGS_DIR

    # AI Detection & Models
    # Primary model is ONNX; fallback is PyTorch .pt
    ONNX_MODEL_PATH = str(MODELS_DIR / "yolov8n.onnx")
    PYTORCH_MODEL_PATH = str(MODELS_DIR / "yolov8n.pt")
    MODEL_PATH = os.getenv("MODEL_PATH", ONNX_MODEL_PATH)
    
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.35))
    IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", 0.45))

    # Supported Vehicle Classes (COCO mapping)
    # 2: car, 3: motorcycle, 5: bus, 7: truck
    COCO_VEHICLE_CLASSES = {
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    }

    # BGR Colors for OpenCV rendering
    CLASS_COLORS_BGR = {
        "car": (255, 191, 0),         # #00BFFF (Deep Sky Blue)
        "motorcycle": (166, 217, 0),   # #00D9A6 (Neon Cyan-Green)
        "bus": (32, 176, 255),         # #FFB020 (Amber Warning)
        "truck": (74, 59, 255),        # #FF3B4A (Vibrant Crimson)
    }

    # HEX Colors for Web UI
    CLASS_COLORS_HEX = {
        "car": "#00BFFF",
        "motorcycle": "#00D9A6",
        "bus": "#FFB020",
        "truck": "#FF3B4A",
    }

    # Tracking Configuration (ByteTrack / Tracker)
    TRACKER_MAX_LOST_FRAMES = int(os.getenv("TRACKER_MAX_LOST_FRAMES", 30))
    TRACKER_MIN_HITS = int(os.getenv("TRACKER_MIN_HITS", 3))
    TRACKER_IOU_THRESHOLD = float(os.getenv("TRACKER_IOU_THRESHOLD", 0.3))

    # Traffic Density & Congestion Thresholds
    DENSITY_LOW_MAX = 35.0      # < 35% is Low
    DENSITY_MED_MAX = 70.0      # 35% - 70% is Medium, >= 70% is High
    
    # Safe road segment capacity (vehicles per 100m lane equivalent)
    DEFAULT_ROAD_CAPACITY = int(os.getenv("DEFAULT_ROAD_CAPACITY", 15))

    # Congestion Score Thresholds (0.0 to 1.0)
    CONGESTION_NORMAL_MAX = 0.40
    CONGESTION_MODERATE_MAX = 0.70

    # Speed Estimation Settings
    FREE_FLOW_SPEED_KMH = float(os.getenv("FREE_FLOW_SPEED_KMH", 60.0))
    
    # Processing & Stream Configuration
    TARGET_WIDTH = int(os.getenv("TARGET_WIDTH", 1280))
    TARGET_HEIGHT = int(os.getenv("TARGET_HEIGHT", 720))
    FRAME_SKIP = int(os.getenv("FRAME_SKIP", 1))
    JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 80))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 500))
    ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

    # Database Configuration
    DATABASE_FILE = DATABASE_DIR / "traffic.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_FILE.as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Telemetry & Persistence interval (seconds)
    STATS_PERSIST_INTERVAL = 5.0
