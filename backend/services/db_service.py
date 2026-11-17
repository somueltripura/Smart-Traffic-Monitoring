import json
import sqlite3
from typing import Any, Dict, List, Optional

from backend.database.db import get_db_connection
from backend.models.entities import Camera, CongestionEvent, SystemLog, TrafficStatistic, VehicleDetection
from backend.utils.logger import setup_logger

logger = setup_logger("DBService")


class DBService:
    """Provides high-level database operations for camera management, detections, and analytics."""

    # --- Camera Management ---

    @staticmethod
    def get_cameras() -> List[Camera]:
        """Fetches all registered traffic cameras."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras ORDER BY created_at ASC;")
        rows = cursor.fetchall()
        return [Camera.from_row(row) for row in rows]

    @staticmethod
    def get_camera_by_id(cam_id: str) -> Optional[Camera]:
        """Retrieves a single camera by ID."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras WHERE id = ?;", (cam_id,))
        row = cursor.fetchone()
        return Camera.from_row(row) if row else None

    @staticmethod
    def create_camera(data: Dict[str, Any]) -> Camera:
        """Registers a new camera node."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cam_id = data.get("id") or f"cam-{int(cursor.execute('SELECT COUNT(*) AS c FROM cameras').fetchone()['c']) + 1:02d}"
        roi_json = json.dumps(data.get("roi_polygon")) if data.get("roi_polygon") else None
        line_json = json.dumps(data.get("counting_line")) if data.get("counting_line") else None
        calib_json = json.dumps(data.get("calibration_params")) if data.get("calibration_params") else None

        cursor.execute("""
            INSERT INTO cameras (
                id, name, location, stream_source, is_active,
                roi_polygon, counting_line, calibration_params,
                road_capacity, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cam_id,
            data.get("name", "New Traffic Camera"),
            data.get("location", "City Location"),
            str(data.get("stream_source", "0")),
            1 if data.get("is_active", True) else 0,
            roi_json,
            line_json,
            calib_json,
            int(data.get("road_capacity", 15)),
            data.get("latitude", 40.7128),
            data.get("longitude", -74.0060),
        ))
        conn.commit()
        logger.info("Created camera: %s (%s)", cam_id, data.get("name"))
        return DBService.get_camera_by_id(cam_id)

    @staticmethod
    def update_camera(cam_id: str, data: Dict[str, Any]) -> Optional[Camera]:
        """Updates camera configuration (ROI, counting line, calibration, etc.)."""
        conn = get_db_connection()
        cursor = conn.cursor()

        fields = []
        values = []

        if "name" in data:
            fields.append("name = ?")
            values.append(data["name"])
        if "location" in data:
            fields.append("location = ?")
            values.append(data["location"])
        if "stream_source" in data:
            fields.append("stream_source = ?")
            values.append(str(data["stream_source"]))
        if "is_active" in data:
            fields.append("is_active = ?")
            values.append(1 if data["is_active"] else 0)
        if "roi_polygon" in data:
            fields.append("roi_polygon = ?")
            values.append(json.dumps(data["roi_polygon"]) if data["roi_polygon"] else None)
        if "counting_line" in data:
            fields.append("counting_line = ?")
            values.append(json.dumps(data["counting_line"]) if data["counting_line"] else None)
        if "calibration_params" in data:
            fields.append("calibration_params = ?")
            values.append(json.dumps(data["calibration_params"]) if data["calibration_params"] else None)
        if "road_capacity" in data:
            fields.append("road_capacity = ?")
            values.append(int(data["road_capacity"]))

        if not fields:
            return DBService.get_camera_by_id(cam_id)

        values.append(cam_id)
        cursor.execute(f"UPDATE cameras SET {', '.join(fields)} WHERE id = ?;", values)
        conn.commit()
        return DBService.get_camera_by_id(cam_id)

    # --- Detections & Statistics Persistence ---

    @staticmethod
    def record_detection(cam_id: str, detection: Dict[str, Any]) -> None:
        """Stores a confirmed crossing event in vehicle_detections."""
        conn = get_db_connection()
        cursor = conn.cursor()
        bbox_json = json.dumps(detection.get("bbox") or detection.get("crossing_point"))
        cursor.execute("""
            INSERT INTO vehicle_detections (
                camera_id, track_id, vehicle_type, confidence,
                direction, speed_kmh, bbox
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cam_id,
            detection.get("track_id", 0),
            detection.get("vehicle_type", "car"),
            float(detection.get("confidence", 0.0)),
            detection.get("direction", "inbound"),
            detection.get("speed_kmh"),
            bbox_json,
        ))
        conn.commit()

    @staticmethod
    def record_statistics(cam_id: str, stats: Dict[str, Any]) -> None:
        """Saves a periodic snapshot in traffic_statistics table."""
        conn = get_db_connection()
        cursor = conn.cursor()
        counts = stats.get("counts", {})

        cursor.execute("""
            INSERT INTO traffic_statistics (
                camera_id, total_vehicles, cars, buses, trucks, motorcycles,
                inbound, outbound, density_percentage, density_level,
                average_speed_kmh, congestion_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cam_id,
            int(counts.get("total_vehicles", 0)),
            int(counts.get("cars", 0)),
            int(counts.get("buses", 0)),
            int(counts.get("trucks", 0)),
            int(counts.get("motorcycles", 0)),
            int(counts.get("inbound", 0)),
            int(counts.get("outbound", 0)),
            float(stats.get("density_percentage", 0.0)),
            stats.get("density_level", "Low"),
            stats.get("average_speed_kmh"),
            stats.get("congestion_level", "Normal"),
        ))
        conn.commit()

    # --- Analytics & Reporting Queries ---

    @staticmethod
    def get_latest_statistics(cam_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent recorded statistics entry."""
        conn = get_db_connection()
        cursor = conn.cursor()

        if cam_id:
            cursor.execute(
                "SELECT * FROM traffic_statistics WHERE camera_id = ? ORDER BY timestamp DESC LIMIT 1;",
                (cam_id,),
            )
        else:
            cursor.execute(
                "SELECT * FROM traffic_statistics ORDER BY timestamp DESC LIMIT 1;"
            )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    @staticmethod
    def get_analytics(cam_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates aggregated metrics, hourly trends, and vehicle category distribution."""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Cumulative totals
        filter_sql = "WHERE camera_id = ?" if cam_id else ""
        params = (cam_id,) if cam_id else ()

        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_records,
                MAX(total_vehicles) as peak_total,
                AVG(density_percentage) as avg_density,
                AVG(average_speed_kmh) as avg_speed,
                SUM(cars) as sum_cars,
                SUM(buses) as sum_buses,
                SUM(trucks) as sum_trucks,
                SUM(motorcycles) as sum_motorcycles
            FROM traffic_statistics {filter_sql};
        """, params)
        agg = cursor.fetchone()

        # Hourly distribution (last 24 hours)
        cursor.execute(f"""
            SELECT 
                strftime('%H:00', timestamp) as hour_bucket,
                AVG(density_percentage) as avg_density,
                AVG(average_speed_kmh) as avg_speed,
                MAX(total_vehicles) as max_vehicles
            FROM traffic_statistics {filter_sql}
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
            LIMIT 24;
        """, params)
        hourly_rows = [dict(r) for r in cursor.fetchall()]

        # Congestion events count
        cursor.execute(f"""
            SELECT severity, COUNT(*) as count 
            FROM congestion_events {filter_sql}
            GROUP BY severity;
        """, params)
        congestion_breakdown = {r["severity"]: r["count"] for r in cursor.fetchall()}

        return {
            "summary": {
                "total_records": agg["total_records"] if agg else 0,
                "peak_total_vehicles": agg["peak_total"] if agg and agg["peak_total"] else 0,
                "average_density_pct": round(agg["avg_density"], 1) if agg and agg["avg_density"] else 0.0,
                "average_speed_kmh": round(agg["avg_speed"], 1) if agg and agg["avg_speed"] else None,
                "vehicle_totals": {
                    "cars": agg["sum_cars"] if agg and agg["sum_cars"] else 0,
                    "buses": agg["sum_buses"] if agg and agg["sum_buses"] else 0,
                    "trucks": agg["sum_trucks"] if agg and agg["sum_trucks"] else 0,
                    "motorcycles": agg["sum_motorcycles"] if agg and agg["sum_motorcycles"] else 0,
                },
            },
            "hourly_trends": hourly_rows,
            "congestion_breakdown": congestion_breakdown,
        }

    @staticmethod
    def get_history(cam_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves raw historical traffic statistics rows."""
        conn = get_db_connection()
        cursor = conn.cursor()
        if cam_id:
            cursor.execute(
                "SELECT * FROM traffic_statistics WHERE camera_id = ? ORDER BY timestamp DESC LIMIT ?;",
                (cam_id, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM traffic_statistics ORDER BY timestamp DESC LIMIT ?;",
                (limit,),
            )
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def record_congestion_event(
        cam_id: str,
        severity: str,
        density_pct: float,
        avg_speed: Optional[float],
    ) -> int:
        """Logs a new congestion event to congestion_events table."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO congestion_events (
                camera_id, severity, density_percentage, average_speed_kmh
            ) VALUES (?, ?, ?, ?)
        """, (cam_id, severity, density_pct, avg_speed))
        conn.commit()
        return cursor.lastrowid
