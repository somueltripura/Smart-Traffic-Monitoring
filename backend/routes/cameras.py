from flask import Blueprint, jsonify, request

from backend.services.db_service import DBService
from backend.services.stream_worker import stream_worker
from backend.utils.logger import setup_logger
from backend.utils.validators import validate_camera_source, validate_counting_line, validate_roi_polygon

logger = setup_logger("CamerasAPI")
cameras_bp = Blueprint("cameras", __name__, url_prefix="/api/cameras")


@cameras_bp.route("", methods=["GET"])
def list_cameras():
    """Lists all registered traffic cameras and active stream states."""
    cameras = DBService.get_cameras()
    cam_dicts = []
    active_cam_id = stream_worker.camera_id if stream_worker.is_active else None

    for cam in cameras:
        d = cam.to_dict()
        d["is_streaming"] = (cam.id == active_cam_id)
        cam_dicts.append(d)

    return jsonify({"cameras": cam_dicts}), 200


@cameras_bp.route("", methods=["POST"])
def add_camera():
    """Registers a new traffic camera source."""
    data = request.get_json(silent=True) or {}
    source = data.get("stream_source")
    if not source:
        return jsonify({"error": "Field 'stream_source' is required."}), 400

    is_valid, msg, parsed_source = validate_camera_source(source)
    if not is_valid:
        return jsonify({"error": msg}), 400

    data["stream_source"] = str(parsed_source)
    new_cam = DBService.create_camera(data)
    return jsonify({
        "message": "Camera registered successfully.",
        "camera": new_cam.to_dict(),
    }), 201


@cameras_bp.route("/<string:cam_id>", methods=["GET"])
def get_camera(cam_id: str):
    """Retrieves metadata and configuration for a specific camera."""
    cam = DBService.get_camera_by_id(cam_id)
    if not cam:
        return jsonify({"error": f"Camera '{cam_id}' not found."}), 404
    return jsonify({"camera": cam.to_dict()}), 200


@cameras_bp.route("/<string:cam_id>/configure", methods=["POST"])
def configure_camera(cam_id: str):
    """Updates ROI polygon, counting line, or calibration parameters dynamically."""
    cam = DBService.get_camera_by_id(cam_id)
    if not cam:
        return jsonify({"error": f"Camera '{cam_id}' not found."}), 404

    data = request.get_json(silent=True) or {}
    updates = {}

    # 1. Counting line configuration
    if "counting_line" in data:
        valid, msg, line = validate_counting_line(data["counting_line"])
        if not valid:
            return jsonify({"error": msg}), 400
        updates["counting_line"] = [list(line[0]), list(line[1])]
        if stream_worker.camera_id == cam_id:
            stream_worker.reconfigure_counting_line(line[0], line[1])

    # 2. ROI Polygon configuration
    if "roi_polygon" in data:
        valid, msg, poly = validate_roi_polygon(data["roi_polygon"])
        if not valid:
            return jsonify({"error": msg}), 400
        updates["roi_polygon"] = [list(pt) for pt in poly]
        if stream_worker.camera_id == cam_id:
            stream_worker.reconfigure_roi(poly)

    # 3. Calibration parameters
    if "calibration_params" in data:
        calib = data["calibration_params"]
        updates["calibration_params"] = calib
        if stream_worker.camera_id == cam_id:
            mode = calib.get("mode", "linear")
            stream_worker.reconfigure_calibration(mode, calib)

    # 4. Road capacity
    if "road_capacity" in data:
        cap_val = max(1, int(data["road_capacity"]))
        updates["road_capacity"] = cap_val
        if stream_worker.camera_id == cam_id:
            stream_worker.density_analyzer.set_capacity(cap_val)

    updated_cam = DBService.update_camera(cam_id, updates)
    return jsonify({
        "message": f"Camera '{cam_id}' configuration updated successfully.",
        "camera": updated_cam.to_dict() if updated_cam else None,
    }), 200
