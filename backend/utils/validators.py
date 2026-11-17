from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import re

from backend.config import Config


def validate_file_extension(filename: str) -> bool:
    """Verifies that uploaded file has an allowed video extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def validate_camera_source(source: Union[str, int]) -> Tuple[bool, str, Union[str, int]]:
    """Validates camera source input (webcam index, local video file, or RTSP/HTTP stream).

    Returns:
        Tuple of (is_valid, message, parsed_source).
    """
    if source is None:
        return False, "Camera source cannot be empty.", source

    source_str = str(source).strip()

    # Check if integer webcam index (e.g., "0", "1")
    if source_str.isdigit():
        return True, "Valid webcam index.", int(source_str)

    # Check if remote stream (RTSP, RTMP, HTTP, HTTPS)
    stream_pattern = re.compile(r"^(rtsp|rtmp|http|https)://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    if stream_pattern.match(source_str):
        return True, "Valid network stream URL.", source_str

    # Check if local video file
    path = Path(source_str)
    if path.is_file():
        if validate_file_extension(path.name):
            return True, "Valid local video file.", str(path.resolve())
        return False, f"Unsupported video file extension: {path.suffix}", source_str

    # Relative to uploads directory
    upload_path = Config.UPLOADS_DIR / source_str
    if upload_path.is_file() and validate_file_extension(upload_path.name):
        return True, "Valid uploaded video file.", str(upload_path.resolve())

    return False, f"Camera source does not exist or format is invalid: {source_str}", source_str


def validate_counting_line(
    coords: Any,
    frame_width: int = 1280,
    frame_height: int = 720,
) -> Tuple[bool, str, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    """Validates two 2D points defining a virtual counting line."""
    if not isinstance(coords, (list, tuple)) or len(coords) != 2:
        return False, "Counting line must contain exactly two points: [[x1, y1], [x2, y2]].", None

    try:
        p1 = coords[0]
        p2 = coords[1]
        x1, y1 = int(round(p1[0])), int(round(p1[1]))
        x2, y2 = int(round(p2[0])), int(round(p2[1]))

        # Boundary checks
        x1 = max(0, min(frame_width, x1))
        y1 = max(0, min(frame_height, y1))
        x2 = max(0, min(frame_width, x2))
        y2 = max(0, min(frame_height, y2))

        if x1 == x2 and y1 == y2:
            return False, "Line start point and end point cannot be identical.", None

        return True, "Valid counting line coordinates.", ((x1, y1), (x2, y2))
    except (ValueError, TypeError, IndexError) as exc:
        return False, f"Invalid point data in counting line: {exc}", None


def validate_roi_polygon(
    points: Any,
    frame_width: int = 1280,
    frame_height: int = 720,
) -> Tuple[bool, str, Optional[List[Tuple[int, int]]]]:
    """Validates a polygon ROI consisting of at least 3 vertices."""
    if not isinstance(points, (list, tuple)) or len(points) < 3:
        return False, "ROI polygon must contain at least 3 vertices.", None

    cleaned_pts: List[Tuple[int, int]] = []
    try:
        for pt in points:
            x, y = int(round(pt[0])), int(round(pt[1]))
            x = max(0, min(frame_width, x))
            y = max(0, min(frame_height, y))
            cleaned_pts.append((x, y))

        return True, "Valid ROI polygon vertices.", cleaned_pts
    except (ValueError, TypeError, IndexError) as exc:
        return False, f"Invalid vertex format: {exc}", None
