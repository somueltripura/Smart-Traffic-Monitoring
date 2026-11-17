from dataclasses import asdict, dataclass
import json
from typing import Any, Dict, List, Optional


@dataclass
class Camera:
    id: str
    name: str
    location: str
    stream_source: str
    is_active: bool = True
    roi_polygon: Optional[List[List[int]]] = None
    counting_line: Optional[List[List[int]]] = None
    calibration_params: Optional[Dict[str, Any]] = None
    road_capacity: int = 15
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Any) -> "Camera":
        roi = json.loads(row["roi_polygon"]) if row["roi_polygon"] else None
        line = json.loads(row["counting_line"]) if row["counting_line"] else None
        calib = json.loads(row["calibration_params"]) if row["calibration_params"] else None

        return cls(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            stream_source=str(row["stream_source"]),
            is_active=bool(row["is_active"]),
            roi_polygon=roi,
            counting_line=line,
            calibration_params=calib,
            road_capacity=int(row["road_capacity"]),
            latitude=float(row["latitude"]) if row["latitude"] is not None else None,
            longitude=float(row["longitude"]) if row["longitude"] is not None else None,
            created_at=str(row["created_at"]) if "created_at" in row.keys() else None,
        )


@dataclass
class VehicleDetection:
    id: Optional[int]
    camera_id: str
    track_id: int
    vehicle_type: str
    confidence: float
    direction: str
    speed_kmh: Optional[float] = None
    bbox: Optional[List[int]] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrafficStatistic:
    id: Optional[int]
    camera_id: str
    total_vehicles: int
    cars: int
    buses: int
    trucks: int
    motorcycles: int
    inbound: int
    outbound: int
    density_percentage: float
    density_level: str
    average_speed_kmh: Optional[float]
    congestion_level: str
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CongestionEvent:
    id: Optional[int]
    camera_id: str
    severity: str
    density_percentage: float
    average_speed_kmh: Optional[float]
    start_time: str
    end_time: Optional[str] = None
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemLog:
    id: Optional[int]
    component: str
    level: str
    message: str
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
