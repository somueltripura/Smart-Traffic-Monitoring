import numpy as np
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.config import Config
from backend.utils.logger import setup_logger

logger = setup_logger("Tracker")


def compute_iou(box1: List[int], box2: List[int]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area) / float(union_area)


class Track:
    """Represents an active tracked vehicle with trajectory history and motion state."""

    def __init__(self, track_id: int, detection: Dict[str, Any]):
        self.track_id = track_id
        self.vehicle_type = detection["vehicle_type"]
        self.class_id = detection["class_id"]
        self.confidence = detection["confidence"]
        self.bbox = detection["bounding_box"]  # [x1, y1, x2, y2]
        
        # Velocity and trajectory
        self.centroid = self._calculate_centroid(self.bbox)
        self.history: List[Tuple[int, int]] = [self.centroid]
        self.max_history_length = 30
        
        self.hits = 1
        self.time_since_update = 0
        self.speed_kmh: Optional[float] = None
        self.pixel_speed: float = 0.0

    @staticmethod
    def _calculate_centroid(bbox: List[int]) -> Tuple[int, int]:
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        return (cx, cy)

    def update(self, detection: Dict[str, Any]) -> None:
        """Updates track with a new detection in the current frame."""
        self.bbox = detection["bounding_box"]
        self.confidence = detection["confidence"]
        self.vehicle_type = detection["vehicle_type"]
        self.class_id = detection["class_id"]

        new_centroid = self._calculate_centroid(self.bbox)
        
        # Instantaneous pixel displacement
        dx = new_centroid[0] - self.centroid[0]
        dy = new_centroid[1] - self.centroid[1]
        self.pixel_speed = float(np.hypot(dx, dy))

        self.centroid = new_centroid
        self.history.append(self.centroid)
        if len(self.history) > self.max_history_length:
            self.history.pop(0)

        self.hits += 1
        self.time_since_update = 0

    def mark_missed(self) -> None:
        """Marks that this track was not associated with any detection in the current frame."""
        self.time_since_update += 1


class VehicleTracker:
    """Multi-Object Vehicle Tracker using two-stage IoU association and trajectory analysis."""

    def __init__(
        self,
        max_lost_frames: int = Config.TRACKER_MAX_LOST_FRAMES,
        min_hits: int = Config.TRACKER_MIN_HITS,
        iou_threshold: float = Config.TRACKER_IOU_THRESHOLD,
    ):
        self.max_lost_frames = max_lost_frames
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold

        self.tracks: Dict[int, Track] = {}
        self.next_track_id = 1
        self.frame_count = 0

    def reset(self) -> None:
        """Resets all active tracks and ID counters."""
        self.tracks.clear()
        self.next_track_id = 1
        self.frame_count = 0
        logger.info("Vehicle tracker reset.")

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Associates incoming detections with active tracks and returns confirmed tracked vehicles.

        Args:
            detections: List of detection dicts from YOLOv8Detector.

        Returns:
            List of confirmed tracked vehicle dicts with track_id and trajectory history.
        """
        self.frame_count += 1

        if not detections:
            # Mark all tracks missed
            for track in list(self.tracks.values()):
                track.mark_missed()
                if track.time_since_update > self.max_lost_frames:
                    del self.tracks[track.track_id]
            return []

        # Split detections into high and low confidence for ByteTrack-style two-stage matching
        high_conf_dets = [d for d in detections if d["confidence"] >= 0.35]
        low_conf_dets = [d for d in detections if d["confidence"] < 0.35]

        # Stage 1: Associate active tracks with high confidence detections
        active_track_ids = list(self.tracks.keys())
        matched_tracks, unmatched_tracks, unmatched_high_dets = self._associate(
            active_track_ids, high_conf_dets, self.iou_threshold
        )

        # Update matched tracks
        for track_id, det_idx in matched_tracks:
            self.tracks[track_id].update(high_conf_dets[det_idx])

        # Stage 2: Try to associate remaining unmatched tracks with low confidence detections
        if unmatched_tracks and low_conf_dets:
            matched_stage2, remaining_unmatched_tracks, _ = self._associate(
                unmatched_tracks, low_conf_dets, iou_threshold=0.20
            )
            for track_id, det_idx in matched_stage2:
                self.tracks[track_id].update(low_conf_dets[det_idx])
            unmatched_tracks = remaining_unmatched_tracks

        # Mark missed tracks
        for track_id in unmatched_tracks:
            self.tracks[track_id].mark_missed()
            if self.tracks[track_id].time_since_update > self.max_lost_frames:
                del self.tracks[track_id]

        # Initialize new tracks for unmatched high confidence detections
        for det_idx in unmatched_high_dets:
            new_track = Track(self.next_track_id, high_conf_dets[det_idx])
            self.tracks[self.next_track_id] = new_track
            self.next_track_id += 1

        # Return confirmed tracks that have accumulated enough hits
        confirmed_tracked_vehicles: List[Dict[str, Any]] = []
        for track in self.tracks.values():
            if track.hits >= self.min_hits and track.time_since_update == 0:
                confirmed_tracked_vehicles.append({
                    "track_id": track.track_id,
                    "vehicle_type": track.vehicle_type,
                    "confidence": track.confidence,
                    "bounding_box": track.bbox,
                    "centroid": track.centroid,
                    "class_id": track.class_id,
                    "history": list(track.history),
                    "speed_kmh": track.speed_kmh,
                    "pixel_speed": track.pixel_speed,
                })

        return confirmed_tracked_vehicles

    def _associate(
        self,
        track_ids: List[int],
        detections: List[Dict[str, Any]],
        iou_threshold: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Greedy IoU association between track bounding boxes and detection boxes."""
        if not track_ids or not detections:
            return [], track_ids, list(range(len(detections)))

        # Build IoU similarity matrix
        iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)
        for i, tid in enumerate(track_ids):
            for j, det in enumerate(detections):
                iou_matrix[i, j] = compute_iou(self.tracks[tid].bbox, det["bounding_box"])

        matched_tracks: List[Tuple[int, int]] = []
        matched_track_indices: Set[int] = set()
        matched_det_indices: Set[int] = set()

        # Sort matches by highest IoU score
        flat_indices = np.argsort(-iou_matrix, axis=None)
        for idx in flat_indices:
            row = int(idx // len(detections))
            col = int(idx % len(detections))
            iou_score = iou_matrix[row, col]

            if iou_score < iou_threshold:
                break

            if row not in matched_track_indices and col not in matched_det_indices:
                matched_tracks.append((track_ids[row], col))
                matched_track_indices.add(row)
                matched_det_indices.add(col)

        unmatched_tracks = [track_ids[i] for i in range(len(track_ids)) if i not in matched_track_indices]
        unmatched_dets = [j for j in range(len(detections)) if j not in matched_det_indices]

        return matched_tracks, unmatched_tracks, unmatched_dets

    def get_tracks_history(self) -> Dict[int, List[Tuple[int, int]]]:
        """Returns trajectory point lists for all confirmed active tracks."""
        return {
            tid: track.history
            for tid, track in self.tracks.items()
            if track.hits >= self.min_hits
        }
