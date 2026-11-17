import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from backend.config import Config
from backend.utils.logger import setup_logger

logger = setup_logger("Density")


class TrafficDensityAnalyzer:
    """Calculates road region vehicle concentration, density percentages, and congestion alerts.

    Documented Calculation Method:
        Density Percentage = min(100.0, (Vehicles Count in Monitored ROI / Safe Road Capacity) * 100.0)
        Where Safe Road Capacity is the maximum number of vehicles safely fitting within the defined
        road segment under standard following distance recommendations.
    """

    def __init__(
        self,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
        capacity: int = Config.DEFAULT_ROAD_CAPACITY,
        low_max: float = Config.DENSITY_LOW_MAX,
        med_max: float = Config.DENSITY_MED_MAX,
        alert_threshold: float = 75.0,
    ):
        """Initializes density analyzer.

        Args:
            roi_polygon: List of (x, y) pixel coordinates defining the road inspection region.
            capacity: Safe road capacity for the defined region.
            low_max: Density ceiling for 'Low' category (< 35%).
            med_max: Density ceiling for 'Medium' category (35% - 70%).
            alert_threshold: Density percentage that triggers a congestion warning.
        """
        self.roi_polygon = roi_polygon or [(120, 280), (1160, 280), (1240, 680), (40, 680)]
        self.capacity = max(1, capacity)
        self.low_max = low_max
        self.med_max = med_max
        self.alert_threshold = alert_threshold

    def set_roi(self, polygon: List[Tuple[int, int]]) -> None:
        """Updates the monitored road polygon region."""
        if len(polygon) >= 3:
            self.roi_polygon = polygon
            logger.info("Monitored ROI updated with %d vertices.", len(polygon))

    def set_capacity(self, capacity: int) -> None:
        """Updates maximum road capacity."""
        self.capacity = max(1, int(capacity))
        logger.info("Road capacity set to: %d", self.capacity)

    def is_inside_roi(self, point: Tuple[int, int]) -> bool:
        """Checks if a 2D coordinate falls within the monitored ROI polygon."""
        if len(self.roi_polygon) < 3:
            return False
        pts = np.array(self.roi_polygon, np.int32)
        # cv2.pointPolygonTest returns > 0 for inside, 0 on edge, < 0 outside
        dist = cv2.pointPolygonTest(pts, (float(point[0]), float(point[1])), measureDist=False)
        return dist >= 0

    def analyze(self, tracked_vehicles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates vehicle density within the designated road section.

        Args:
            tracked_vehicles: List of confirmed tracked vehicles.

        Returns:
            Dictionary containing density metrics, classification, and alert status.
        """
        vehicles_in_roi: List[int] = []
        class_breakdown = {"cars": 0, "buses": 0, "trucks": 0, "motorcycles": 0}

        for vehicle in tracked_vehicles:
            # Bottom center point is most accurate for ground road surface position
            bbox = vehicle["bounding_box"]
            ground_pt = ((bbox[0] + bbox[2]) // 2, bbox[3])

            if self.is_inside_roi(ground_pt):
                tid = vehicle["track_id"]
                vehicles_in_roi.append(tid)
                vtype = vehicle.get("vehicle_type", "car").lower()
                if vtype in class_breakdown:
                    class_breakdown[vtype] += 1
                else:
                    class_breakdown["cars"] += 1

        count_in_roi = len(vehicles_in_roi)
        raw_pct = (count_in_roi / float(self.capacity)) * 100.0
        density_pct = round(min(100.0, raw_pct), 1)

        # Classify density level
        if density_pct < self.low_max:
            density_level = "Low"
        elif density_pct < self.med_max:
            density_level = "Medium"
        else:
            density_level = "High"

        congestion_alert = density_pct >= self.alert_threshold

        return {
            "vehicles_in_roi": count_in_roi,
            "road_capacity": self.capacity,
            "density_percentage": density_pct,
            "density_level": density_level,
            "congestion_alert": congestion_alert,
            "class_breakdown": class_breakdown,
            "monitored_vehicle_ids": vehicles_in_roi,
            "calculation_method": "Vehicles in defined ROI / Safe Road Capacity Ratio",
        }
