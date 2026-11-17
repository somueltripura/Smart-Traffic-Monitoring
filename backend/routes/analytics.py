from flask import Blueprint, jsonify, request

from backend.services.db_service import DBService
from backend.utils.logger import setup_logger

logger = setup_logger("AnalyticsAPI")
analytics_bp = Blueprint("analytics", __name__, url_prefix="/api")


@analytics_bp.route("/analytics", methods=["GET"])
def get_analytics():
    """Returns aggregated traffic analytics, hourly volume trends, and congestion statistics."""
    camera_id = request.args.get("camera_id")
    analytics_data = DBService.get_analytics(camera_id)
    return jsonify(analytics_data), 200


@analytics_bp.route("/history", methods=["GET"])
def get_history():
    """Returns raw time-series historical traffic records."""
    camera_id = request.args.get("camera_id")
    limit = int(request.args.get("limit", 100))
    history_records = DBService.get_history(camera_id, limit=limit)
    return jsonify({"history": history_records}), 200
