import cv2
import json
import numpy as np
import time
from flask import Blueprint, Response

from backend.services.stream_worker import stream_worker
from backend.utils.logger import setup_logger

logger = setup_logger("StreamRouter")
stream_bp = Blueprint("stream", __name__, url_prefix="/api/stream")


def generate_standby_frame(message: str = "SYSTEM STANDBY - CLICK START") -> bytes:
    """Creates a dark sci-fi placeholder frame when video stream is paused or offline."""
    w, h = 1280, 720
    img = np.full((h, w, 3), (7, 17, 31), dtype=np.uint8)  # #07111F

    # Grid pattern
    for x in range(0, w, 40):
        cv2.line(img, (x, 0), (x, h), (16, 34, 56), 1)
    for y in range(0, h, 40):
        cv2.line(img, (0, y), (w, y), (16, 34, 56), 1)

    # Center box
    box_w, box_h = 560, 160
    bx1 = (w - box_w) // 2
    by1 = (h - box_h) // 2
    cv2.rectangle(img, (bx1, by1), (bx1 + box_w, by1 + box_h), (16, 34, 56), -1)
    cv2.rectangle(img, (bx1, by1), (bx1 + box_w, by1 + box_h), (0, 191, 255), 2)

    # Text
    cv2.putText(
        img,
        "SMART TRAFFIC MONITORING SYSTEM",
        (bx1 + 40, by1 + 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 191, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        img,
        message,
        (bx1 + 70, by1 + 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 217, 166),
        1,
        cv2.LINE_AA,
    )

    _, jpeg = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return jpeg.tobytes()


def video_stream_generator():
    """Generates continuous MJPEG multipart frame stream."""
    standby_bytes = generate_standby_frame()
    
    while True:
        if stream_worker.is_active:
            frame_bytes = stream_worker.get_frame()
            if frame_bytes is None:
                frame_bytes = standby_bytes
        else:
            frame_bytes = standby_bytes

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
        time.sleep(0.033)  # ~30 FPS throttle


@stream_bp.route("/video", methods=["GET"])
def live_video_stream():
    """MJPEG Live video stream endpoint for dashboard viewer."""
    return Response(
        video_stream_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def sse_telemetry_generator():
    """Generates Server-Sent Events (SSE) telemetry data stream at ~2 Hz."""
    while True:
        telemetry = stream_worker.get_telemetry()
        payload = json.dumps(telemetry)
        yield f"event: traffic_update\ndata: {payload}\n\n"
        time.sleep(0.5)


@stream_bp.route("/events", methods=["GET"])
def sse_events_stream():
    """Server-Sent Events endpoint for real-time telemetry streaming to web UI."""
    return Response(
        sse_telemetry_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
