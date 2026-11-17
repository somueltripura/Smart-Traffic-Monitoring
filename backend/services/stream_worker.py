from collections import deque
from pathlib import Path
import cv2
import numpy as np
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.config import Config
from backend.detection.counter import VehicleCounter
from backend.detection.density import TrafficDensityAnalyzer
from backend.detection.detector import YOLOv8Detector
from backend.detection.speed import SpeedEstimator
from backend.detection.tracker import VehicleTracker
from backend.services.db_service import DBService
from backend.utils.drawing import Visualizer
from backend.utils.logger import setup_logger

logger = setup_logger("StreamWorker")


class StreamWorker:
    """Manages dedicated background video ingestion, AI detection, and telemetry generation."""

    def __init__(self, camera_id: str = "cam-01"):
        self.camera_id = camera_id
        self.source: Union[str, int] = "0"
        self.is_active = False

        # Threading controls
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        # Core CV & Analytics Modules
        self.detector = YOLOv8Detector()
        self.tracker = VehicleTracker()
        self.counter = VehicleCounter()
        self.density_analyzer = TrafficDensityAnalyzer()
        self.speed_estimator = SpeedEstimator(fps=30.0)
        self.visualizer = Visualizer()

        # Buffers
        self.latest_jpeg: Optional[bytes] = None
        self.latest_telemetry: Dict[str, Any] = self._initial_telemetry()
        self.fps_meter = deque(maxlen=20)
        self.current_fps = 0.0

        # Persistence timers
        self.last_persist_time = time.time()
        self.last_congestion_status = "Normal"

    def _initial_telemetry(self) -> Dict[str, Any]:
        """Provides default structured telemetry state."""
        return {
            "camera_id": self.camera_id,
            "status": "idle",
            "fps": 0.0,
            "vehicle_counts": {
                "cars": 0,
                "buses": 0,
                "trucks": 0,
                "motorcycles": 0,
                "total_vehicles": 0,
                "inbound": 0,
                "outbound": 0,
            },
            "density": {
                "vehicles_in_roi": 0,
                "road_capacity": Config.DEFAULT_ROAD_CAPACITY,
                "density_percentage": 0.0,
                "density_level": "Low",
                "congestion_alert": False,
            },
            "speed": {
                "average_speed_kmh": None,
                "average_pixel_speed": 0.0,
                "is_calibrated": False,
            },
            "congestion": {
                "status": "Normal",
                "score": 0.0,
            },
            "active_tracks_count": 0,
            "recent_crossings": [],
            "timestamp": time.time(),
        }

    def start(self, source: Union[str, int], camera_id: Optional[str] = None) -> bool:
        """Starts video capture and inference worker thread."""
        with self.lock:
            if self.is_active:
                logger.info("Worker already running. Stopping previous stream first.")
                self._stop_internal()

            if camera_id:
                self.camera_id = camera_id

            self.source = source
            self.stop_event.clear()
            self.is_active = True

            # Load camera specific ROI/Line/Calibration settings from DB
            self._load_camera_configuration()

            self.thread = threading.Thread(
                target=self._run_loop,
                name=f"Worker-{self.camera_id}",
                daemon=True,
            )
            self.thread.start()
            logger.info("StreamWorker started for camera '%s' with source: %s", self.camera_id, self.source)
            return True

    def stop(self) -> None:
        """Stops the running worker thread."""
        with self.lock:
            self._stop_internal()

    def _stop_internal(self) -> None:
        if self.is_active:
            self.is_active = False
            self.stop_event.set()
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            logger.info("StreamWorker stopped for camera: %s", self.camera_id)

    def _load_camera_configuration(self) -> None:
        """Loads saved camera geometries and calibration settings from database."""
        try:
            cam = DBService.get_camera_by_id(self.camera_id)
            if cam:
                if cam.roi_polygon and len(cam.roi_polygon) >= 3:
                    pts = [tuple(p) for p in cam.roi_polygon]
                    self.density_analyzer.set_roi(pts)
                if cam.counting_line and len(cam.counting_line) == 2:
                    p1 = tuple(cam.counting_line[0])
                    p2 = tuple(cam.counting_line[1])
                    self.counter.set_line(p1, p2)
                if cam.road_capacity:
                    self.density_analyzer.set_capacity(cam.road_capacity)
                if cam.calibration_params:
                    params = cam.calibration_params
                    if params.get("mode") == "linear" and params.get("meters_per_pixel"):
                        self.speed_estimator.set_linear_scale(float(params["meters_per_pixel"]))
                    elif params.get("mode") == "homography" and params.get("src") and params.get("dims"):
                        self.speed_estimator.set_homography(params["src"], params["dims"])
        except Exception as exc:
            logger.warning("Could not load camera DB config: %s", exc)

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        """Opens video capture device with retry logic."""
        source = self.source
        if isinstance(source, str):
            if source.isdigit():
                source = int(source)
            elif not Path(source).is_file():
                upload_file = Config.UPLOADS_DIR / source
                if upload_file.is_file():
                    source = str(upload_file.resolve())

        logger.info("Opening VideoCapture on resolved source: %s", source)
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error("Failed to open video capture source: %s", self.source)
            return None

        logger.info("VideoCapture opened successfully: %s", source)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _run_loop(self) -> None:
        """Main processing loop executing capture, inference, tracking, and telemetry."""
        try:
            cap = self._open_capture()
            if not cap:
                self.is_active = False
                return

            fps_val = cap.get(cv2.CAP_PROP_FPS)
            if fps_val and fps_val > 5:
                self.speed_estimator.fps = fps_val

            frame_idx = 0
            skip_counter = 0

            while not self.stop_event.is_set():
                loop_start = time.time()
                ret, frame = cap.read()

                if frame_idx == 0:
                    logger.info("First frame read: ret=%s, frame=%s", ret, frame.shape if frame is not None else None)

                if not ret or frame is None:
                    # If reading video file, rewind to start for continuous live playback
                    if isinstance(self.source, str) and not self.source.isdigit() and not self.source.startswith("rtsp"):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        time.sleep(0.05)
                        continue
                    else:
                        logger.warning("Stream read failed. Attempting reconnect in 1.0s...")
                        time.sleep(1.0)
                        cap.release()
                        cap = self._open_capture()
                        if not cap:
                            break
                        continue

                frame_idx += 1
                skip_counter += 1
                if skip_counter < Config.FRAME_SKIP:
                    continue
                skip_counter = 0

                # 1. Detection
                detections = self.detector.detect(frame)

                # 2. Tracking
                tracked_vehicles = self.tracker.update(detections)

                # 3. Virtual Line Counting
                counter_result = self.counter.update(tracked_vehicles)
                counts = counter_result["statistics"]
                new_crossings = counter_result["newly_counted"]

                # Persist newly crossed vehicles
                for event in new_crossings:
                    try:
                        DBService.record_detection(self.camera_id, event)
                    except Exception as exc:
                        logger.warning("Failed to record vehicle detection: %s", exc)

                # 4. Traffic Density
                density_data = self.density_analyzer.analyze(tracked_vehicles)

                # 5. Speed Estimation
                tracked_vehicles, avg_speed_kmh, avg_px_speed = self.speed_estimator.estimate_speeds(
                    tracked_vehicles, frame_idx
                )

                # 6. Congestion Classification
                congestion_status, congestion_score = self._compute_congestion(
                    density_data["density_percentage"],
                    avg_speed_kmh,
                    tracked_vehicles,
                )

                # Check for congestion events
                if congestion_status == "High Congestion" and self.last_congestion_status != "High Congestion":
                    try:
                        DBService.record_congestion_event(
                            self.camera_id,
                            severity="High",
                            density_pct=density_data["density_percentage"],
                            avg_speed=avg_speed_kmh,
                        )
                    except Exception as exc:
                        logger.warning("Failed to record congestion event: %s", exc)
                self.last_congestion_status = congestion_status

                # Calculate FPS
                loop_time = time.time() - loop_start
                instant_fps = 1.0 / loop_time if loop_time > 0 else 30.0
                self.fps_meter.append(instant_fps)
                self.current_fps = round(float(np.mean(self.fps_meter)), 1)

                # 7. Visualization & Overlays
                annotated_frame = self.visualizer.draw_detections(frame, tracked_vehicles)
                annotated_frame = self.visualizer.draw_trajectories(
                    annotated_frame, self.tracker.get_tracks_history()
                )
                annotated_frame = self.visualizer.draw_counting_line(
                    annotated_frame,
                    self.counter.line_coords,
                    inbound_count=counts.get("inbound", 0),
                    outbound_count=counts.get("outbound", 0),
                )
                annotated_frame = self.visualizer.draw_roi_polygon(
                    annotated_frame,
                    self.density_analyzer.roi_polygon,
                    density_level=density_data["density_level"],
                    density_pct=density_data["density_percentage"],
                )
                annotated_frame = self.visualizer.draw_hud(
                    annotated_frame,
                    fps=self.current_fps,
                    counts=counts,
                    density_pct=density_data["density_percentage"],
                    congestion_status=congestion_status,
                    avg_speed=avg_speed_kmh,
                )

                # Encode annotated frame as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), Config.JPEG_QUALITY]
                success, jpeg_buffer = cv2.imencode(".jpg", annotated_frame, encode_param)

                # Update thread-safe latest frame and telemetry snapshot
                telemetry_snapshot = {
                    "camera_id": self.camera_id,
                    "status": "online",
                    "fps": self.current_fps,
                    "vehicle_counts": counts,
                    "density": density_data,
                    "speed": {
                        "average_speed_kmh": avg_speed_kmh,
                        "average_pixel_speed": avg_px_speed,
                        "is_calibrated": self.speed_estimator.is_calibrated,
                    },
                    "congestion": {
                        "status": congestion_status,
                        "score": round(congestion_score, 2),
                    },
                    "active_tracks_count": len(tracked_vehicles),
                    "recent_crossings": counter_result.get("recent_crossings", []),
                    "timestamp": time.time(),
                }

                with self.lock:
                    if success:
                        self.latest_jpeg = jpeg_buffer.tobytes()
                    self.latest_telemetry = telemetry_snapshot

                # Periodic statistics persistence to database
                now = time.time()
                if now - self.last_persist_time >= Config.STATS_PERSIST_INTERVAL:
                    self.last_persist_time = now
                    try:
                        DBService.record_statistics(
                            self.camera_id,
                            {
                                "counts": counts,
                                "density_percentage": density_data["density_percentage"],
                                "density_level": density_data["density_level"],
                                "average_speed_kmh": avg_speed_kmh,
                                "congestion_level": congestion_status,
                            },
                        )
                    except Exception as exc:
                        logger.warning("Failed to record traffic stats snapshot: %s", exc)

            cap.release()
            logger.info("VideoCapture released for camera: %s", self.camera_id)
        except Exception as exc:
            logger.exception("Fatal error in stream processing loop: %s", exc)
        finally:
            self.is_active = False

    def _compute_congestion(
        self,
        density_pct: float,
        avg_speed_kmh: Optional[float],
        tracked_vehicles: List[Dict[str, Any]],
    ) -> Tuple[str, float]:
        """Calculates composite congestion score and returns (status, score)."""
        # Density factor (0.0 to 1.0)
        d_factor = min(1.0, density_pct / 100.0)

        # Speed factor (if calibrated)
        if avg_speed_kmh is not None and Config.FREE_FLOW_SPEED_KMH > 0:
            speed_ratio = avg_speed_kmh / Config.FREE_FLOW_SPEED_KMH
            s_factor = max(0.0, 1.0 - speed_ratio)
        else:
            s_factor = 0.0

        # Stationary vehicle ratio
        stationary_count = sum(1 for v in tracked_vehicles if v.get("pixel_speed", 0) < 1.0)
        stat_ratio = stationary_count / max(1, len(tracked_vehicles))

        # Composite score
        if avg_speed_kmh is not None:
            score = 0.50 * d_factor + 0.35 * s_factor + 0.15 * stat_ratio
        else:
            score = 0.80 * d_factor + 0.20 * stat_ratio

        if score < Config.CONGESTION_NORMAL_MAX:
            status = "Normal"
        elif score < Config.CONGESTION_MODERATE_MAX:
            status = "Moderate"
        else:
            status = "High Congestion"

        return status, float(score)

    def get_frame(self) -> Optional[bytes]:
        """Returns the latest annotated JPEG frame bytes."""
        with self.lock:
            return self.latest_jpeg

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns the current real-time telemetry state."""
        with self.lock:
            return dict(self.latest_telemetry)

    # Dynamic Reconfiguration
    def reconfigure_roi(self, polygon: List[Tuple[int, int]]) -> None:
        self.density_analyzer.set_roi(polygon)

    def reconfigure_counting_line(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        self.counter.set_line(p1, p2)

    def reconfigure_thresholds(self, conf: Optional[float], iou: Optional[float]) -> None:
        self.detector.set_thresholds(conf, iou)

    def reconfigure_calibration(self, mode: str, params: Dict[str, Any]) -> None:
        if mode == "linear" and "meters_per_pixel" in params:
            self.speed_estimator.set_linear_scale(float(params["meters_per_pixel"]))
        elif mode == "homography" and "src" in params and "dims" in params:
            self.speed_estimator.set_homography(params["src"], params["dims"])


# Global singleton worker instance for the active monitoring session
stream_worker = StreamWorker()
