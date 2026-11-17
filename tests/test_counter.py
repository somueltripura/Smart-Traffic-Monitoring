import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.counter import VehicleCounter, segments_intersect


class TestVehicleCounter(unittest.TestCase):
    """Test suite for VehicleCounter and line crossing detection."""

    def test_segment_intersection(self):
        # Crossing segments
        p1, p2 = (0, 10), (20, 10)    # Horizontal line at y=10
        p3, p4 = (10, 0), (10, 20)    # Vertical line at x=10
        self.assertTrue(segments_intersect(p1, p2, p3, p4))

        # Parallel non-intersecting
        p5, p6 = (0, 20), (20, 20)
        self.assertFalse(segments_intersect(p1, p2, p5, p6))

    def test_counting_and_deduplication(self):
        # Line across y=300
        counter = VehicleCounter(line_coords=((0, 300), (800, 300)))

        # Vehicle moving from y=250 to y=350 (crosses line)
        vehicle1 = {
            "track_id": 1,
            "vehicle_type": "car",
            "confidence": 0.95,
            "bounding_box": [100, 300, 150, 350],
            "history": [(125, 250), (125, 350)],
        }

        result = counter.update([vehicle1])
        counts = result["statistics"]
        self.assertEqual(counts["cars"], 1)
        self.assertEqual(counts["total_vehicles"], 1)
        self.assertEqual(len(result["newly_counted"]), 1)

        # Frame 2: Vehicle continues moving to y=400 (should NOT count again!)
        vehicle1_f2 = {
            "track_id": 1,
            "vehicle_type": "car",
            "confidence": 0.95,
            "bounding_box": [100, 350, 150, 400],
            "history": [(125, 350), (125, 400)],
        }
        result2 = counter.update([vehicle1_f2])
        counts2 = result2["statistics"]
        self.assertEqual(counts2["cars"], 1)
        self.assertEqual(counts2["total_vehicles"], 1)
        self.assertEqual(len(result2["newly_counted"]), 0)

        # Vehicle 2: A bus crossing line
        vehicle2 = {
            "track_id": 2,
            "vehicle_type": "bus",
            "confidence": 0.92,
            "bounding_box": [300, 300, 400, 350],
            "history": [(350, 250), (350, 350)],
        }
        result3 = counter.update([vehicle2])
        counts3 = result3["statistics"]
        self.assertEqual(counts3["cars"], 1)
        self.assertEqual(counts3["buses"], 1)
        self.assertEqual(counts3["total_vehicles"], 2)


if __name__ == "__main__":
    unittest.main()
