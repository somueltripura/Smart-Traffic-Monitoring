import unittest
import numpy as np
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection.detector import YOLOv8Detector
from backend.config import Config


class TestYOLOv8Detector(unittest.TestCase):
    """Unit test suite for YOLOv8 Vehicle Detector."""

    @classmethod
    def setUpClass(cls):
        cls.detector = YOLOv8Detector(
            model_path=str(Config.MODELS_DIR / "yolov8.onnx"),
            conf_threshold=0.30,
            iou_threshold=0.45,
        )

    def test_detector_initialization(self):
        """Validates that detector loads model and initializes ONNX session."""
        self.assertIsNotNone(self.detector)
        self.assertIn(self.detector.backend, ["onnxruntime", "opencv_dnn"])
        self.assertEqual(self.detector.input_width, 640)
        self.assertEqual(self.detector.input_height, 640)

    def test_empty_and_blank_frames(self):
        """Verifies graceful handling of empty or blank video frames."""
        # None frame
        self.assertEqual(self.detector.detect(None), [])
        
        # Zero-sized frame
        zero_frame = np.empty((0, 0, 3), dtype=np.uint8)
        self.assertEqual(self.detector.detect(zero_frame), [])

        # Pure black frame (no vehicles should be detected)
        black_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        results = self.detector.detect(black_frame)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_threshold_updating(self):
        """Tests dynamic reconfiguration of confidence and IoU thresholds."""
        self.detector.set_thresholds(conf_threshold=0.55, iou_threshold=0.60)
        self.assertAlmostEqual(self.detector.conf_threshold, 0.55)
        self.assertAlmostEqual(self.detector.iou_threshold, 0.60)

        # Restore default
        self.detector.set_thresholds(conf_threshold=0.35, iou_threshold=0.45)

    def test_detection_structure(self):
        """Validates schema adherence for detection output."""
        # Test on dummy synthetic frame
        test_frame = np.full((720, 1280, 3), 120, dtype=np.uint8)
        results = self.detector.detect(test_frame)
        self.assertIsInstance(results, list)
        for det in results:
            self.assertIn("vehicle_type", det)
            self.assertIn("confidence", det)
            self.assertIn("bounding_box", det)
            self.assertIn("class_id", det)
            self.assertIn(det["vehicle_type"], ["car", "motorcycle", "bus", "truck"])
            x1, y1, x2, y2 = det["bounding_box"]
            self.assertGreaterEqual(x2, x1)
            self.assertGreaterEqual(y2, y1)


if __name__ == "__main__":
    unittest.main()
