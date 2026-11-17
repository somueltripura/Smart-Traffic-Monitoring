import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.speed import SpeedEstimator


class TestSpeedEstimator(unittest.TestCase):
    """Test suite for SpeedEstimator and calibration modes."""

    def test_uncalibrated_mode(self):
        estimator = SpeedEstimator(fps=30.0)
        self.assertFalse(estimator.is_calibrated)

        # Vehicle moving
        v = {
            "track_id": 1,
            "vehicle_type": "car",
            "bounding_box": [100, 100, 150, 150],
        }

        # Feed positions across 10 frames
        for frame_idx in range(10):
            v["bounding_box"] = [100, 100 + frame_idx * 5, 150, 150 + frame_idx * 5]
            vehicles, avg_speed, avg_px = estimator.estimate_speeds([v], frame_idx)

        # Speed must be None / unavailable when uncalibrated!
        self.assertIsNone(vehicles[0]["speed_kmh"])
        self.assertEqual(vehicles[0]["speed_status"], "unavailable")
        self.assertGreater(vehicles[0]["pixel_speed"], 0.0)

    def test_calibrated_mode(self):
        # 1 pixel = 0.05 meters (5 cm per pixel)
        estimator = SpeedEstimator(fps=30.0, meters_per_pixel=0.05)
        self.assertTrue(estimator.is_calibrated)

        v = {
            "track_id": 1,
            "vehicle_type": "car",
            "bounding_box": [100, 100, 150, 150],
        }

        # 10 pixels per frame displacement at 30 fps = 300 px/sec
        # 300 px/sec * 0.05 m/px = 15 m/sec = 54 km/h!
        for frame_idx in range(12):
            v["bounding_box"] = [100, 100 + frame_idx * 10, 150, 150 + frame_idx * 10]
            vehicles, avg_speed, _ = estimator.estimate_speeds([v], frame_idx)

        self.assertIsNotNone(vehicles[0]["speed_kmh"])
        self.assertEqual(vehicles[0]["speed_status"], "calibrated")
        # Check near 54 km/h (allowing floating point/smoothing margin)
        self.assertAlmostEqual(vehicles[0]["speed_kmh"], 54.0, delta=2.0)
        self.assertAlmostEqual(avg_speed, 54.0, delta=2.0)


if __name__ == "__main__":
    unittest.main()
