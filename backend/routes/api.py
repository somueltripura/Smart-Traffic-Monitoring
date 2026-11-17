from datetime import datetime, timezone
import os
from pathlib import Path
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from backend.config import Config
from backend.services.db_service import DBService
from backend.services.stream_worker import stream_worker
from backend.utils.logger import setup_logger
from backend.utils.validators import validate_camera_source, validate_file_extension

logger = setup_logger("API")
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health status and component checks."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_model": {
            "loaded": stream_worker.detector is not None,
            "backend": stream_worker.detector.backend if stream_worker.detector else None,
            "model_path": stream_worker.detector.model_path if stream_worker.detector else None,
        },
        "worker": {
            "active": stream_worker.is_active,
            "camera_id": stream_worker.camera_id,
            "fps": stream_worker.current_fps,
        },
    }), 200


@api_bp.route("/traffic", methods=["GET"])
def get_traffic_telemetry():
    """Returns combined real-time traffic statistics, density, speed, and congestion state."""
    telemetry = stream_worker.get_telemetry()
    return jsonify(telemetry), 200


@api_bp.route("/traffic/counts", methods=["GET"])
def get_vehicle_counts():
    """Returns live vehicle category counts and directional stats."""
    telemetry = stream_worker.get_telemetry()
    return jsonify({
        "camera_id": telemetry.get("camera_id"),
        "counts": telemetry.get("vehicle_counts", {}),
        "recent_crossings": telemetry.get("recent_crossings", []),
        "timestamp": telemetry.get("timestamp"),
    }), 200


@api_bp.route("/traffic/density", methods=["GET"])
def get_traffic_density():
    """Returns current traffic density percentage, level, and alert status."""
    telemetry = stream_worker.get_telemetry()
    return jsonify({
        "camera_id": telemetry.get("camera_id"),
        "density": telemetry.get("density", {}),
        "timestamp": telemetry.get("timestamp"),
    }), 200


@api_bp.route("/traffic/speed", methods=["GET"])
def get_traffic_speed():
    """Returns average vehicle speed in km/h or uncalibrated movement indicator."""
    telemetry = stream_worker.get_telemetry()
    return jsonify({
        "camera_id": telemetry.get("camera_id"),
        "speed": telemetry.get("speed", {}),
        "timestamp": telemetry.get("timestamp"),
    }), 200


@api_bp.route("/traffic/congestion", methods=["GET"])
def get_traffic_congestion():
    """Returns real-time congestion classification (Normal, Moderate, High Congestion)."""
    telemetry = stream_worker.get_telemetry()
    return jsonify({
        "camera_id": telemetry.get("camera_id"),
        "congestion": telemetry.get("congestion", {}),
        "timestamp": telemetry.get("timestamp"),
    }), 200


@api_bp.route("/detection/start", methods=["POST"])
def start_detection():
    """Starts video processing and monitoring for a selected camera or uploaded video."""
    data = request.get_json(silent=True) or {}
    camera_id = data.get("camera_id", "cam-01")
    custom_source = data.get("source")

    cam = DBService.get_camera_by_id(camera_id)
    if not cam and not custom_source:
        return jsonify({"error": f"Camera '{camera_id}' not found."}), 404

    source = custom_source or (cam.stream_source if cam else "0")
    is_valid, msg, parsed_source = validate_camera_source(source)

    if not is_valid:
        return jsonify({"error": msg}), 400

    success = stream_worker.start(parsed_source, camera_id=camera_id)
    if success:
        return jsonify({
            "message": f"Detection monitoring started successfully on {camera_id}.",
            "camera_id": camera_id,
            "source": str(parsed_source),
        }), 200
    else:
        return jsonify({"error": "Failed to start detection worker."}), 500


@api_bp.route("/detection/stop", methods=["POST"])
def stop_detection():
    """Stops the active video processing worker."""
    stream_worker.stop()
    return jsonify({
        "message": "Detection monitoring stopped.",
        "camera_id": stream_worker.camera_id,
    }), 200


@api_bp.route("/upload", methods=["POST"])
def upload_video():
    """Uploads a traffic video file for AI analysis."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file."}), 400

    if not validate_file_extension(file.filename):
        return jsonify({
            "error": f"Invalid file format. Allowed extensions: {list(Config.ALLOWED_EXTENSIONS)}"
        }), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    save_path = Config.UPLOADS_DIR / saved_filename

    try:
        file.save(str(save_path))
        logger.info("Uploaded video saved to: %s", save_path)

        # Auto-create or attach to a custom camera entry
        cam_data = {
            "name": f"Uploaded: {filename}",
            "location": "Uploaded Video Analysis",
            "stream_source": saved_filename,
            "is_active": True,
            "road_capacity": 15,
        }
        new_cam = DBService.create_camera(cam_data)

        return jsonify({
            "message": "Video uploaded successfully.",
            "filename": saved_filename,
            "camera_id": new_cam.id,
            "path": str(save_path),
        }), 201
    except Exception as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        return jsonify({"error": f"Failed to upload video: {str(exc)}"}), 500
