import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from backend.config import Config


class Visualizer:
    """Renders professional overlays, HUD telemetry, bounding boxes, ROIs, and counting lines."""

    def __init__(self):
        self.class_colors = Config.CLASS_COLORS_BGR
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def get_color(self, vehicle_type: str) -> Tuple[int, int, int]:
        """Returns BGR color assigned to vehicle type."""
        return self.class_colors.get(vehicle_type.lower(), (255, 255, 255))

    def draw_corner_box(
        self,
        img: np.ndarray,
        box: List[int],
        color: Tuple[int, int, int],
        thickness: int = 2,
        corner_length: int = 15,
    ) -> None:
        """Draws modern corner brackets around the bounding box."""
        x1, y1, x2, y2 = box
        
        # Base rectangle with light opacity
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

        # Top-Left
        cv2.line(img, (x1, y1), (x1 + corner_length, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y1), (x1, y1 + corner_length), color, thickness, cv2.LINE_AA)

        # Top-Right
        cv2.line(img, (x2, y1), (x2 - corner_length, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y1), (x2, y1 + corner_length), color, thickness, cv2.LINE_AA)

        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + corner_length, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y2), (x1, y2 - corner_length), color, thickness, cv2.LINE_AA)

        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - corner_length, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2, y2 - corner_length), color, thickness, cv2.LINE_AA)

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        show_confidence: bool = True,
    ) -> np.ndarray:
        """Renders vehicle bounding boxes, category tags, and confidence scores.

        Args:
            frame: Target BGR video frame.
            detections: List of detection dictionaries.
            show_confidence: Whether to append confidence percentage.

        Returns:
            Frame with annotated detections.
        """
        annotated = frame.copy()

        for det in detections:
            vtype = det.get("vehicle_type", "vehicle")
            conf = det.get("confidence", 0.0)
            x1, y1, x2, y2 = det.get("bounding_box", [0, 0, 0, 0])
            track_id = det.get("track_id")
            speed = det.get("speed_kmh")

            color = self.get_color(vtype)
            self.draw_corner_box(annotated, [x1, y1, x2, y2], color, thickness=2)

            # Construct label
            label_parts = [f"#{track_id}" if track_id is not None else "", vtype.upper()]
            if show_confidence:
                label_parts.append(f"{conf:.2f}")
            if speed is not None and speed > 0:
                label_parts.append(f"{speed:.1f} km/h")

            label = " ".join([p for p in label_parts if p])

            # Label dimensions
            font_scale = 0.45
            font_thickness = 1
            (label_w, label_h), baseline = cv2.getTextSize(
                label, self.font, font_scale, font_thickness
            )

            # Badge background
            pill_y1 = max(0, y1 - label_h - 8)
            pill_y2 = y1
            pill_x1 = x1
            pill_x2 = x1 + label_w + 10

            # Fill badge
            cv2.rectangle(
                annotated,
                (pill_x1, pill_y1),
                (pill_x2, pill_y2),
                (16, 34, 56),  # #102238 card dark background
                cv2.FILLED,
            )
            cv2.rectangle(
                annotated,
                (pill_x1, pill_y1),
                (pill_x2, pill_y2),
                color,
                1,
                cv2.LINE_AA,
            )

            # Draw text
            text_pos = (pill_x1 + 5, pill_y2 - 4)
            cv2.putText(
                annotated,
                label,
                text_pos,
                self.font,
                font_scale,
                (255, 255, 255),
                font_thickness,
                cv2.LINE_AA,
            )

        return annotated

    def draw_trajectories(
        self, frame: np.ndarray, tracks_history: Dict[int, List[Tuple[int, int]]]
    ) -> np.ndarray:
        """Renders trailing motion paths for tracked vehicles."""
        for track_id, points in tracks_history.items():
            if len(points) < 2:
                continue

            for i in range(1, len(points)):
                # Fade trajectory line backwards
                alpha = float(i) / float(len(points))
                thickness = int(np.clip(alpha * 3, 1, 3))
                pt1 = points[i - 1]
                pt2 = points[i]
                cv2.line(frame, pt1, pt2, (0, 217, 166), thickness, cv2.LINE_AA)
        return frame

    def draw_roi_polygon(
        self,
        frame: np.ndarray,
        polygon: List[Tuple[int, int]],
        density_level: str = "Low",
        density_pct: float = 0.0,
    ) -> np.ndarray:
        """Renders a semi-transparent road density inspection zone."""
        if len(polygon) < 3:
            return frame

        pts = np.array(polygon, np.int32).reshape((-1, 1, 2))
        overlay = frame.copy()

        level_colors = {
            "Low": (0, 217, 166),         # Neon Cyan-Green
            "Medium": (32, 176, 255),      # Amber Warning
            "High": (74, 59, 255),         # Crimson Danger
        }
        color = level_colors.get(density_level, (0, 191, 255))

        # Semi-transparent fill
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.20, frame, 0.80, 0, frame)

        # Polygon perimeter border
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)

        # Label zone
        center_x = int(np.mean([p[0] for p in polygon]))
        center_y = int(np.mean([p[1] for p in polygon]))
        badge_text = f"ROI: {density_level.upper()} ({density_pct:.1f}%)"
        cv2.putText(
            frame,
            badge_text,
            (center_x - 60, center_y),
            self.font,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
        return frame

    def draw_counting_line(
        self,
        frame: np.ndarray,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]],
        inbound_count: int = 0,
        outbound_count: int = 0,
    ) -> np.ndarray:
        """Renders the virtual counting line with directional indicators."""
        p1, p2 = line_coords
        line_color = (0, 191, 255)  # #00BFFF Electric Blue

        # Draw main counting barrier
        cv2.line(frame, p1, p2, line_color, 3, cv2.LINE_AA)
        
        # End markers
        cv2.circle(frame, p1, 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, p2, 5, (255, 255, 255), -1, cv2.LINE_AA)

        # Midpoint badge
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2

        count_badge = f"IN: {inbound_count} | OUT: {outbound_count}"
        cv2.putText(
            frame,
            count_badge,
            (mid_x - 70, mid_y - 12),
            self.font,
            0.50,
            (0, 191, 255),
            2,
            cv2.LINE_AA,
        )
        return frame

    def draw_hud(
        self,
        frame: np.ndarray,
        fps: float,
        counts: Dict[str, int],
        density_pct: float,
        congestion_status: str,
        avg_speed: Optional[float] = None,
    ) -> np.ndarray:
        """Renders top futuristic HUD status bar."""
        h, w = frame.shape[:2]
        hud_height = 42

        # Dark overlay banner at the top
        hud_bg = frame[0:hud_height, 0:w].copy()
        cv2.rectangle(frame, (0, 0), (w, hud_height), (7, 17, 31), cv2.FILLED)
        cv2.addWeighted(hud_bg, 0.20, frame[0:hud_height, 0:w], 0.80, 0, frame[0:hud_height, 0:w])
        cv2.line(frame, (0, hud_height), (w, hud_height), (0, 191, 255), 1, cv2.LINE_AA)

        # Section 1: System FPS
        fps_text = f"AI ENGINE: ONNX | {fps:.1f} FPS"
        cv2.putText(frame, fps_text, (15, 26), self.font, 0.48, (0, 217, 166), 1, cv2.LINE_AA)

        # Section 2: Vehicle totals
        total = counts.get("total_vehicles", 0)
        cars = counts.get("cars", 0)
        buses = counts.get("buses", 0)
        trucks = counts.get("trucks", 0)
        motos = counts.get("motorcycles", 0)
        counts_text = f"VEHICLES: {total} (C:{cars} B:{buses} T:{trucks} M:{motos})"
        cv2.putText(frame, counts_text, (w // 4, 26), self.font, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

        # Section 3: Density & Congestion
        cong_colors = {
            "Normal": (0, 217, 166),
            "Moderate": (32, 176, 255),
            "High Congestion": (74, 59, 255),
        }
        cong_color = cong_colors.get(congestion_status, (0, 217, 166))
        status_text = f"DENSITY: {density_pct:.1f}% | {congestion_status.upper()}"
        cv2.putText(frame, status_text, (w - 380, 26), self.font, 0.48, cong_color, 1, cv2.LINE_AA)

        # Section 4: Average Speed
        speed_text = f"{avg_speed:.1f} km/h" if avg_speed is not None else "UNSET"
        cv2.putText(frame, f"AVG: {speed_text}", (w - 110, 26), self.font, 0.48, (0, 191, 255), 1, cv2.LINE_AA)

        return frame
