import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.tracker import VehicleTracker, compute_iou


class TestVehicleTracker(unittest.TestCase):
    """Test suite for VehicleTracker and IoU computation."""

    def test_compute_iou(self):
        # Identical boxes
        self.assertAlmostEqual(compute_iou([10, 10, 50, 50], [10, 10, 50, 50]), 1.0)
        # Disjoint boxes
        self.assertEqual(compute_iou([0, 0, 10, 10], [20, 20, 30, 30]), 0.0)
        # Half overlap
        box1 = [0, 0, 20, 20]  # area 400
        box2 = [10, 0, 30, 20]  # area 400, inter 200, union 600 -> iou 1/3
        self.assertAlmostEqual(compute_iou(box1, box2), 1.0 / 3.0)

    def test_tracking_lifecycle(self):
        tracker = VehicleTracker(min_hits=2, max_lost_frames=5)

        # Frame 1: Detection of a car
        det1 = [{
            "vehicle_type": "car",
            "confidence": 0.90,
            "bounding_box": [100, 100, 200, 200],
            "class_id": 2,
        }]
        # First frame does not confirm yet because min_hits=2
        tracks = tracker.update(det1)
        self.assertEqual(len(tracks), 0)

        # Frame 2: Same car slightly displaced
        det2 = [{
            "vehicle_type": "car",
            "confidence": 0.88,
            "bounding_box": [105, 102, 205, 202],
            "class_id": 2,
        }]
        tracks = tracker.update(det2)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["track_id"], 1)
        self.assertEqual(tracks[0]["vehicle_type"], "car")

        # Frame 3: Missing detection (occlusion)
        tracks = tracker.update([])
        self.assertEqual(len(tracks), 0)

        # Frame 4: Car reappears near previous spot
        det4 = [{
            "vehicle_type": "car",
            "confidence": 0.85,
            "bounding_box": [110, 105, 210, 205],
            "class_id": 2,
        }]
        tracks = tracker.update(det4)
        self.assertEqual(len(tracks), 1)
        # Verify track ID is preserved across occlusion!
        self.assertEqual(tracks[0]["track_id"], 1)


if __name__ == "__main__":
    unittest.main()
