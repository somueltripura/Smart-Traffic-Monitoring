import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.config import Config
from backend.utils.logger import setup_logger

logger = setup_logger("Database")

# Thread-local storage for SQLite connections (ensures multi-thread safety)
_local = threading.local()


def get_db_connection() -> sqlite3.Connection:
    """Returns a thread-local SQLite connection with dictionary row access."""
    if not hasattr(_local, "connection") or _local.connection is None:
        db_path = Config.DATABASE_FILE
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect with WAL mode enabled for high concurrent throughput
        conn = sqlite3.connect(
            str(db_path),
            timeout=15.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _local.connection = conn
    return _local.connection


def init_database() -> None:
    """Creates database tables and default cameras if not already present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. cameras table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            stream_source TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            roi_polygon TEXT,
            counting_line TEXT,
            calibration_params TEXT,
            road_capacity INTEGER DEFAULT 15,
            latitude REAL,
            longitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. vehicle_detections table (persisted upon crossing, avoiding per-frame disk bloat)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            track_id INTEGER NOT NULL,
            vehicle_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            direction TEXT NOT NULL,
            speed_kmh REAL,
            bbox TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (camera_id) REFERENCES cameras (id)
        );
    """)

    # 3. traffic_statistics table (throttled periodic snapshots)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traffic_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            total_vehicles INTEGER NOT NULL,
            cars INTEGER NOT NULL,
            buses INTEGER NOT NULL,
            trucks INTEGER NOT NULL,
            motorcycles INTEGER NOT NULL,
            inbound INTEGER DEFAULT 0,
            outbound INTEGER DEFAULT 0,
            density_percentage REAL NOT NULL,
            density_level TEXT NOT NULL,
            average_speed_kmh REAL,
            congestion_level TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (camera_id) REFERENCES cameras (id)
        );
    """)

    # 4. congestion_events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS congestion_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            density_percentage REAL NOT NULL,
            average_speed_kmh REAL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            is_resolved INTEGER DEFAULT 0,
            FOREIGN KEY (camera_id) REFERENCES cameras (id)
        );
    """)

    # 5. system_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    logger.info("Database schema initialized successfully.")

    # Seed initial camera records if empty
    _seed_default_cameras(conn)


def _seed_default_cameras(conn: sqlite3.Connection) -> None:
    """Inserts default mock/sample camera nodes for immediate out-of-the-box operation."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM cameras;")
    count = cursor.fetchone()["cnt"]

    if count == 0:
        default_roi = json.dumps([[120, 280], [1160, 280], [1240, 680], [40, 680]])
        default_line = json.dumps([[100, 480], [1180, 480]])
        default_calib = json.dumps({"mode": "linear", "meters_per_pixel": 0.05, "is_calibrated": True})

        sample_cameras = [
            (
                "cam-01",
                "Downtown Metro Junction",
                "Grand Avenue & 5th St",
                "demo_traffic.mp4",  # Ready-to-run demo video clip
                1,
                default_roi,
                default_line,
                default_calib,
                15,
                40.7128,
                -74.0060,
            ),
            (
                "cam-02",
                "North Expressway Corridor",
                "Interstate 95 - Mile 42",
                "demo_highway.mp4",
                0,
                default_roi,
                default_line,
                default_calib,
                25,
                40.7282,
                -73.9942,
            ),
            (
                "cam-03",
                "Harbor Gateway Bridge",
                "South Coastal Crossing",
                "demo_bridge.mp4",
                0,
                default_roi,
                default_line,
                default_calib,
                20,
                40.7014,
                -74.0150,
            ),
        ]

        cursor.executemany("""
            INSERT INTO cameras (
                id, name, location, stream_source, is_active,
                roi_polygon, counting_line, calibration_params,
                road_capacity, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_cameras)
        conn.commit()
        logger.info("Seeded %d default cameras.", len(sample_cameras))
