import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from backend.utils.logger import setup_logger

logger = setup_logger("Speed")


class SpeedEstimator:
    """Estimates real-world vehicle speed using camera perspective homography and reference calibration.
    
    Adheres strictly to the requirement:
    - If calibration is configured: Computes real ground displacement in meters and speed in km/h.
    - If calibration is unconfigured: Flags speed as unavailable and reports pixel displacement (px/s).
    """

    def __init__(
        self,
        fps: float = 30.0,
        homography_src: Optional[List[Tuple[int, int]]] = None,
        real_world_dimensions: Optional[Tuple[float, float]] = None,
        meters_per_pixel: Optional[float] = None,
    ):
        """Initializes speed estimator.

        Args:
            fps: Frame rate of the video source (default 30.0).
            homography_src: 4 quad vertices on image [top-left, top-right, bottom-right, bottom-left].
            real_world_dimensions: (length_meters, width_meters) of the quadrilateral road section.
            meters_per_pixel: Alternative linear scale factor.
        """
        self.fps = max(1.0, float(fps))
        self.is_calibrated = False
        self.homography_matrix: Optional[np.ndarray] = None
        self.meters_per_pixel: Optional[float] = None

        # Speed smoothing histories: track_id -> List of recent speeds
        self.speed_history: Dict[int, List[float]] = {}
        # Track position history with timestamps: track_id -> List of (point, frame_idx)
        self.position_history: Dict[int, List[Tuple[Tuple[int, int], int]]] = {}

        if homography_src and real_world_dimensions and len(homography_src) == 4:
            self.set_homography(homography_src, real_world_dimensions)
        elif meters_per_pixel is not None and meters_per_pixel > 0:
            self.set_linear_scale(meters_per_pixel)

    def set_homography(
        self,
        src_points: List[Tuple[int, int]],
        dimensions_meters: Tuple[float, float],
    ) -> bool:
        """Calibrates speed using 4-point perspective transformation.

        Args:
            src_points: 4 road quadrilateral corners in pixel space.
            dimensions_meters: (length_meters, width_meters) of the road section.
        """
        if len(src_points) != 4:
            logger.warning("Homography requires exactly 4 source vertices.")
            return False

        length_m, width_m = dimensions_meters
        if length_m <= 0 or width_m <= 0:
            return False

        src = np.array(src_points, dtype=np.float32)
        # Metric destination coordinates in meters (0,0) to (width, length)
        dst = np.array([
            [0.0, 0.0],
            [width_m, 0.0],
            [width_m, length_m],
            [0.0, length_m],
        ], dtype=np.float32)

        try:
            self.homography_matrix = cv2.getPerspectiveTransform(src, dst)
            self.is_calibrated = True
            self.meters_per_pixel = None
            logger.info("Camera speed perspective calibrated successfully (Homography mode).")
            return True
        except Exception as exc:
            logger.error("Failed to compute homography matrix: %s", exc)
            self.is_calibrated = False
            return False

    def set_linear_scale(self, meters_per_pixel: float) -> bool:
        """Calibrates speed using a direct metric scale factor."""
        if meters_per_pixel > 0:
            self.meters_per_pixel = float(meters_per_pixel)
            self.homography_matrix = None
            self.is_calibrated = True
            logger.info("Camera speed calibrated (Linear scale: %.4f m/px).", self.meters_per_pixel)
            return True
        return False

    def reset_calibration(self) -> None:
        """Resets calibration to uncalibrated mode."""
        self.is_calibrated = False
        self.homography_matrix = None
        self.meters_per_pixel = None
        logger.info("Camera speed calibration reset to uncalibrated.")

    def _transform_point(self, point: Tuple[int, int]) -> Tuple[float, float]:
        """Transforms image pixel coordinate to real-world metric coordinates."""
        if self.homography_matrix is not None:
            pt = np.array([[[float(point[0]), float(point[1])]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(pt, self.homography_matrix)
            return float(transformed[0][0][0]), float(transformed[0][0][1])
        elif self.meters_per_pixel is not None:
            return float(point[0]) * self.meters_per_pixel, float(point[1]) * self.meters_per_pixel
        return float(point[0]), float(point[1])

    def estimate_speeds(
        self,
        tracked_vehicles: List[Dict[str, Any]],
        frame_idx: int,
    ) -> Tuple[List[Dict[str, Any]], Optional[float], float]:
        """Calculates instantaneous and smoothed speeds for tracked vehicles.

        Args:
            tracked_vehicles: Active tracked vehicles list.
            frame_idx: Monotonically increasing frame index.

        Returns:
            Tuple of:
            - Updated tracked vehicles list with speed fields.
            - Average scene speed in km/h (or None if uncalibrated).
            - Average pixel speed (px/s).
        """
        active_speeds: List[float] = []
        active_pixel_speeds: List[float] = []
        sample_window_frames = max(3, int(self.fps * 0.25))  # ~0.25 second window

        active_tids = {v["track_id"] for v in tracked_vehicles}
        
        # Clean up stale tracks
        for tid in list(self.position_history.keys()):
            if tid not in active_tids:
                del self.position_history[tid]
                self.speed_history.pop(tid, None)

        for vehicle in tracked_vehicles:
            tid = vehicle["track_id"]
            bbox = vehicle["bounding_box"]
            ground_pt = ((bbox[0] + bbox[2]) // 2, bbox[3])

            if tid not in self.position_history:
                self.position_history[tid] = []

            self.position_history[tid].append((ground_pt, frame_idx))
            if len(self.position_history[tid]) > 20:
                self.position_history[tid].pop(0)

            history = self.position_history[tid]
            
            # Need at least sample_window_frames for reliable displacement measurement
            if len(history) >= sample_window_frames:
                prev_pt, prev_frame = history[-sample_window_frames]
                curr_pt, curr_frame = history[-1]
                frame_diff = curr_frame - prev_frame

                if frame_diff > 0:
                    time_elapsed = frame_diff / self.fps
                    
                    # Pixel speed
                    pixel_dist = float(np.hypot(curr_pt[0] - prev_pt[0], curr_pt[1] - prev_pt[1]))
                    pixel_speed = pixel_dist / time_elapsed
                    vehicle["pixel_speed"] = round(pixel_speed, 1)
                    active_pixel_speeds.append(pixel_speed)

                    if self.is_calibrated:
                        # Metric displacement in real meters
                        real_curr = self._transform_point(curr_pt)
                        real_prev = self._transform_point(prev_pt)
                        meters_dist = float(np.hypot(real_curr[0] - real_prev[0], real_curr[1] - real_prev[1]))

                        # Speed in km/h
                        speed_mps = meters_dist / time_elapsed
                        instant_kmh = speed_mps * 3.6

                        # Filter noise
                        if instant_kmh < 2.0:
                            instant_kmh = 0.0  # stationary threshold
                        elif instant_kmh > 200.0:
                            instant_kmh = 200.0  # physical road ceiling

                        # Exponential Moving Average (EMA) smoothing
                        if tid not in self.speed_history:
                            self.speed_history[tid] = [instant_kmh]
                        else:
                            self.speed_history[tid].append(instant_kmh)
                            if len(self.speed_history[tid]) > 5:
                                self.speed_history[tid].pop(0)

                        smoothed_kmh = float(np.mean(self.speed_history[tid]))
                        vehicle["speed_kmh"] = round(smoothed_kmh, 1)
                        vehicle["speed_status"] = "calibrated"
                        active_speeds.append(smoothed_kmh)
                    else:
                        vehicle["speed_kmh"] = None
                        vehicle["speed_status"] = "unavailable"
            else:
                vehicle["speed_kmh"] = None
                vehicle["speed_status"] = "calibrating" if self.is_calibrated else "unavailable"
                vehicle["pixel_speed"] = 0.0

        avg_speed_kmh = round(float(np.mean(active_speeds)), 1) if active_speeds else None
        avg_pixel_speed = round(float(np.mean(active_pixel_speeds)), 1) if active_pixel_speeds else 0.0

        return tracked_vehicles, avg_speed_kmh, avg_pixel_speed
