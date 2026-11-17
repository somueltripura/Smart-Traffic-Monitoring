from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

from backend.config import Config
from backend.utils.logger import setup_logger

logger = setup_logger("Detector")


class YOLOv8Detector:
    """High-performance YOLOv8 Vehicle Detector supporting ONNX Runtime and OpenCV DNN.
    
    Filters specifically for:
    - Cars (COCO ID 2)
    - Motorcycles (COCO ID 3)
    - Buses (COCO ID 5)
    - Trucks (COCO ID 7)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        input_size: Tuple[int, int] = (640, 640),
    ):
        """Initializes the detector with model weights and inference thresholds.

        Args:
            model_path: Absolute or relative path to the ONNX model file.
            conf_threshold: Minimum detection confidence threshold (0.0 to 1.0).
            iou_threshold: Non-Maximum Suppression IoU threshold (0.0 to 1.0).
            input_size: Input resolution (width, height) expected by YOLOv8.
        """
        self.model_path = model_path or Config.ONNX_MODEL_PATH
        self.conf_threshold = conf_threshold or Config.CONFIDENCE_THRESHOLD
        self.iou_threshold = iou_threshold or Config.IOU_THRESHOLD
        self.input_width, self.input_height = input_size
        self.target_classes = Config.COCO_VEHICLE_CLASSES
        
        self.session = None
        self.net = None
        self.backend = None
        
        self._load_model()
        self._warmup()

    def _load_model(self) -> None:
        """Loads model into ONNX Runtime or falls back to OpenCV DNN."""
        model_file = Path(self.model_path)
        if not model_file.is_file():
            # Try alternate path in Config
            alt_path = Config.MODELS_DIR / "yolov8.onnx"
            if alt_path.is_file():
                self.model_path = str(alt_path)
                model_file = alt_path
            else:
                raise FileNotFoundError(f"Model file not found at: {self.model_path}")

        logger.info("Loading YOLOv8 ONNX model from: %s", self.model_path)

        if HAS_ONNX:
            try:
                # Optimized session options
                opts = ort.SessionOptions()
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.intra_op_num_threads = 4
                opts.inter_op_num_threads = 2
                
                # Available providers (CPU fallback guaranteed)
                providers = ["CPUExecutionProvider"]
                if "CUDAExecutionProvider" in ort.get_available_providers():
                    providers.insert(0, "CUDAExecutionProvider")

                self.session = ort.InferenceSession(
                    self.model_path,
                    sess_options=opts,
                    providers=providers,
                )
                self.input_name = self.session.get_inputs()[0].name
                self.output_name = self.session.get_outputs()[0].name
                self.backend = "onnxruntime"
                logger.info(
                    "ONNX Runtime initialized successfully with providers: %s",
                    self.session.get_providers(),
                )
                return
            except Exception as exc:
                logger.warning("Failed to initialize ONNX Runtime: %s. Falling back to OpenCV DNN.", exc)

        # OpenCV DNN Fallback
        try:
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self.backend = "opencv_dnn"
            logger.info("OpenCV DNN backend initialized successfully.")
        except Exception as exc:
            logger.error("Failed to load model using OpenCV DNN: %s", exc)
            raise RuntimeError(f"Could not load YOLOv8 model: {exc}")

    def _warmup(self) -> None:
        """Performs a dummy inference forward pass to eliminate first-frame latency."""
        try:
            dummy_img = np.zeros((self.input_height, self.input_width, 3), dtype=np.uint8)
            self.detect(dummy_img)
            logger.info("Detector warmed up successfully.")
        except Exception as exc:
            logger.warning("Warmup inference warning: %s", exc)

    def set_thresholds(
        self,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ) -> None:
        """Dynamically updates confidence and IoU thresholds.

        Args:
            conf_threshold: New confidence threshold (0.05 to 1.0).
            iou_threshold: New IoU threshold (0.1 to 1.0).
        """
        if conf_threshold is not None:
            self.conf_threshold = max(0.05, min(1.0, float(conf_threshold)))
        if iou_threshold is not None:
            self.iou_threshold = max(0.1, min(1.0, float(iou_threshold)))
        logger.debug(
            "Thresholds updated: conf=%.2f, iou=%.2f",
            self.conf_threshold,
            self.iou_threshold,
        )

    def _letterbox(
        self,
        img: np.ndarray,
        new_shape: Tuple[int, int] = (640, 640),
        color: Tuple[int, int, int] = (114, 114, 114),
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Resizes and pads image to preserve aspect ratio for YOLOv8 input.

        Args:
            img: Source BGR image from OpenCV.
            new_shape: Desired (width, height) tuple.
            color: Padding border color (default 114 gray).

        Returns:
            Tuple of (letterboxed_image, scale_ratio, (pad_left, pad_top)).
        """
        shape = img.shape[:2]  # [height, width]
        target_w, target_h = new_shape

        # Scale ratio (new / old)
        r = min(target_w / shape[1], target_h / shape[0])

        # Compute padding
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = target_w - new_unpad[0]
        dh = target_h - new_unpad[1]

        dw /= 2.0  # divide padding into 2 sides
        dh /= 2.0

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

        img = cv2.copyMakeBorder(
            img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        return img, r, (left, top)

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Executes vehicle detection on an input video frame.

        Args:
            frame: Raw BGR frame as NumPy ndarray (H, W, 3).

        Returns:
            List of detection dicts:
            [
              {
                "vehicle_type": "car",
                "confidence": 0.95,
                "bounding_box": [x1, y1, x2, y2],
                "class_id": 2
              },
              ...
            ]
        """
        if frame is None or frame.size == 0:
            return []

        orig_h, orig_w = frame.shape[:2]

        # 1. Preprocessing (letterbox + transpose + normalize)
        padded_img, scale, (pad_x, pad_y) = self._letterbox(
            frame, (self.input_width, self.input_height)
        )
        
        # BGR to RGB
        blob = cv2.cvtColor(padded_img, cv2.COLOR_BGR2RGB)
        # Normalize to [0, 1] and HWC -> CHW -> NCHW
        blob = blob.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)

        # 2. Forward pass inference
        if self.backend == "onnxruntime":
            outputs = self.session.run([self.output_name], {self.input_name: blob})
            raw_output = outputs[0]  # shape: [1, 84, 8400]
        else:
            self.net.setInput(blob)
            raw_output = self.net.forward()

        # 3. Postprocessing
        predictions = np.squeeze(raw_output)  # shape: [84, 8400]
        predictions = np.transpose(predictions)  # shape: [8400, 84]

        boxes = []
        confidences = []
        class_ids = []

        # Target class keys (integers)
        valid_coco_ids = set(self.target_classes.keys())

        for pred in predictions:
            classes_scores = pred[4:]
            max_class_id = int(np.argmax(classes_scores))
            max_score = float(classes_scores[max_class_id])

            if max_class_id in valid_coco_ids and max_score >= self.conf_threshold:
                # YOLO format: [center_x, center_y, width, height] in letterbox space
                cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]

                # Convert to top-left corner and width/height for NMS
                x1_pad = cx - w / 2.0
                y1_pad = cy - h / 2.0

                # Rescale to original frame dimensions
                x1 = (x1_pad - pad_x) / scale
                y1 = (y1_pad - pad_y) / scale
                box_w = w / scale
                box_h = h / scale

                # Boundary clipping
                x1 = max(0, min(orig_w - 1, int(round(x1))))
                y1 = max(0, min(orig_h - 1, int(round(y1))))
                box_w = max(1, min(orig_w - x1, int(round(box_w))))
                box_h = max(1, min(orig_h - y1, int(round(box_h))))

                boxes.append([x1, y1, box_w, box_h])
                confidences.append(max_score)
                class_ids.append(max_class_id)

        if not boxes:
            return []

        # 4. Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, self.conf_threshold, self.iou_threshold
        )

        detections: List[Dict[str, Any]] = []
        if len(indices) > 0:
            flat_indices = indices.flatten() if hasattr(indices, "flatten") else indices
            for idx in flat_indices:
                x, y, w, h = boxes[idx]
                cid = class_ids[idx]
                vehicle_type = self.target_classes.get(cid, "vehicle")
                conf = round(float(confidences[idx]), 4)
                
                # Format: [x1, y1, x2, y2]
                bbox = [int(x), int(y), int(x + w), int(y + h)]

                detections.append({
                    "vehicle_type": vehicle_type,
                    "confidence": conf,
                    "bounding_box": bbox,
                    "class_id": cid,
                })

        return detections
