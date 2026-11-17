import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.density import TrafficDensityAnalyzer


class TestTrafficDensity(unittest.TestCase):
    """Test suite for TrafficDensityAnalyzer."""

    def test_density_levels_and_containment(self):
        # Monitored ROI polygon from (100, 100) to (500, 500)
        roi = [(100, 100), (500, 100), (500, 500), (100, 500)]
        analyzer = TrafficDensityAnalyzer(roi_polygon=roi, capacity=10)

        # Vehicle inside ROI
        v_in = {
            "track_id": 1,
            "vehicle_type": "car",
            "bounding_box": [200, 200, 250, 250],  # ground pt: (225, 250)
        }
        # Vehicle outside ROI
        v_out = {
            "track_id": 2,
            "vehicle_type": "truck",
            "bounding_box": [600, 600, 680, 680],  # ground pt: (640, 680)
        }

        analysis = analyzer.analyze([v_in, v_out])
        self.assertEqual(analysis["vehicles_in_roi"], 1)
        self.assertEqual(analysis["road_capacity"], 10)
        self.assertEqual(analysis["density_percentage"], 10.0)
        self.assertEqual(analysis["density_level"], "Low")
        self.assertFalse(analysis["congestion_alert"])

        # High density test: 8 vehicles inside capacity 10 -> 80% (High + Alert)
        many_vehicles = [
            {
                "track_id": i,
                "vehicle_type": "car",
                "bounding_box": [150 + i * 20, 150 + i * 20, 190 + i * 20, 190 + i * 20],
            }
            for i in range(8)
        ]
        high_analysis = analyzer.analyze(many_vehicles)
        self.assertEqual(high_analysis["vehicles_in_roi"], 8)
        self.assertEqual(high_analysis["density_percentage"], 80.0)
        self.assertEqual(high_analysis["density_level"], "High")
        self.assertTrue(high_analysis["congestion_alert"])


if __name__ == "__main__":
    unittest.main()
