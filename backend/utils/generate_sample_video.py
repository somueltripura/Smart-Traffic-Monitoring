import cv2
import numpy as np
from pathlib import Path

from backend.config import Config


def generate_sample_traffic_video(
    output_path: str = "smart-traffic-monitoring/uploads/demo_traffic.mp4",
    num_frames: int = 240,
    fps: int = 30,
) -> str:
    """Generates a synthetic traffic video with road lanes and moving vehicles for test validation."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(out_file), fourcc, fps, (w, h))

    # Road coordinates (perspective quad)
    road_pts = np.array([[200, 150], [1080, 150], [1280, 720], [0, 720]], np.int32)

    # Vehicles data: [x, y, speed_y, width, height, color, label]
    vehicles = [
        {"x": 380, "y": 180, "vy": 4, "w": 65, "h": 90, "color": (255, 191, 0), "type": "car"},
        {"x": 620, "y": 250, "vy": 3, "w": 90, "h": 170, "color": (32, 176, 255), "type": "bus"},
        {"x": 840, "y": 160, "vy": 5, "w": 50, "h": 80, "color": (166, 217, 0), "type": "car"},
        {"x": 480, "y": 320, "vy": 2.5, "w": 100, "h": 180, "color": (74, 59, 255), "type": "truck"},
        {"x": 760, "y": 210, "vy": 6, "w": 30, "h": 50, "color": (0, 217, 166), "type": "motorcycle"},
    ]

    for frame_i in range(num_frames):
        frame = np.full((h, w, 3), (35, 45, 55), dtype=np.uint8)

        # Draw Asphalt Road
        cv2.fillPoly(frame, [road_pts], (60, 65, 70))
        cv2.polylines(frame, [road_pts], True, (200, 200, 200), 2)

        # Draw Lane Dividers
        for lane_x_ratio in [0.35, 0.50, 0.65]:
            p_top = (int(w * lane_x_ratio), 150)
            p_bot = (int(w * (lane_x_ratio * 1.4 - 0.2)), 720)
            cv2.line(frame, p_top, p_bot, (255, 255, 255), 2, cv2.LINE_AA)

        # Update and render vehicles
        for v in vehicles:
            vx = int(v["x"])
            vy = int(v["y"])
            vw = int(v["w"])
            vh = int(v["h"])

            # Vehicle body
            cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), v["color"], -1)
            # Windshield / details
            cv2.rectangle(frame, (vx + 5, vy + 10), (vx + vw - 5, vy + 30), (20, 20, 20), -1)

            # Move downwards
            v["y"] += v["vy"]
            # Loop around if past bottom
            if v["y"] > h:
                v["y"] = 120 + (frame_i % 40)

        out.write(frame)

    out.release()
    print(f"Sample traffic video generated at: {out_file} ({out_file.stat().st_size} bytes)")
    return str(out_file)


if __name__ == "__main__":
    generate_sample_traffic_video()
