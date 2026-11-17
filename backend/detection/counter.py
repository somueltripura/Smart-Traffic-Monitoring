from typing import Any, Dict, List, Optional, Set, Tuple

from backend.utils.logger import setup_logger

logger = setup_logger("Counter")


def ccw(a: Tuple[int, int], b: Tuple[int, int], c: Tuple[int, int]) -> float:
    """Computes orientation of triplet (a, b, c) via 2D cross-product."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    p3: Tuple[int, int],
    p4: Tuple[int, int],
) -> bool:
    """Determines if segment (p1, p2) intersects with segment (p3, p4)."""
    d1 = ccw(p1, p2, p3)
    d2 = ccw(p1, p2, p4)
    d3 = ccw(p3, p4, p1)
    d4 = ccw(p3, p4, p2)

    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
        and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


class VehicleCounter:
    """Maintains deduplicated vehicle counts and directional statistics across a virtual counting line."""

    def __init__(
        self,
        line_coords: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    ):
        """Initializes counter with line coordinates.

        Args:
            line_coords: Tuple of ((x1, y1), (x2, y2)). Defaults to (100, 480) -> (1180, 480).
        """
        self.line_coords = line_coords or ((100, 480), (1180, 480))
        
        # Category counters
        self.counts = {
            "cars": 0,
            "buses": 0,
            "trucks": 0,
            "motorcycles": 0,
            "total_vehicles": 0,
            "inbound": 0,
            "outbound": 0,
        }
        
        # Deduplication registry
        self.counted_ids: Set[int] = set()
        # Most recent cross events for real-time live feed
        self.recent_crossings: List[Dict[str, Any]] = []

    def set_line(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> None:
        """Configures virtual counting line coordinates."""
        self.line_coords = (p1, p2)
        logger.info("Counting line set to: %s -> %s", p1, p2)

    def reset(self) -> None:
        """Resets all vehicle counts and deduplication registries."""
        for key in self.counts:
            self.counts[key] = 0
        self.counted_ids.clear()
        self.recent_crossings.clear()
        logger.info("Vehicle counter statistics reset.")

    def update(self, tracked_vehicles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates vehicle trajectories against the counting line.

        Args:
            tracked_vehicles: List of confirmed tracked vehicle dicts from VehicleTracker.

        Returns:
            Dictionary of current vehicle statistics and newly counted events.
        """
        new_events: List[Dict[str, Any]] = []
        p1, p2 = self.line_coords

        # Normal vector for directional calculation
        lx = p2[0] - p1[0]
        ly = p2[1] - p1[1]
        normal_x = -ly
        normal_y = lx

        for vehicle in tracked_vehicles:
            tid = vehicle["track_id"]
            history = vehicle.get("history", [])

            if tid in self.counted_ids or len(history) < 2:
                continue

            # Trajectory segment between last two frames
            prev_pt = history[-2]
            curr_pt = history[-1]

            if segments_intersect(p1, p2, prev_pt, curr_pt):
                # Vehicle crossed the virtual line!
                self.counted_ids.add(tid)

                # Direction determination
                vx = curr_pt[0] - prev_pt[0]
                vy = curr_pt[1] - prev_pt[1]
                dot_product = vx * normal_x + vy * normal_y
                direction = "inbound" if dot_product > 0 else "outbound"

                vtype = vehicle["vehicle_type"].lower()
                
                # Category tallying
                if vtype == "car":
                    self.counts["cars"] += 1
                elif vtype == "bus":
                    self.counts["buses"] += 1
                elif vtype == "truck":
                    self.counts["trucks"] += 1
                elif vtype in ["motorcycle", "motorbike"]:
                    self.counts["motorcycles"] += 1
                else:
                    self.counts["cars"] += 1

                self.counts["total_vehicles"] += 1
                self.counts[direction] += 1

                event_data = {
                    "track_id": tid,
                    "vehicle_type": vtype,
                    "confidence": vehicle.get("confidence", 0.0),
                    "direction": direction,
                    "speed_kmh": vehicle.get("speed_kmh"),
                    "crossing_point": curr_pt,
                }
                new_events.append(event_data)
                self.recent_crossings.append(event_data)
                if len(self.recent_crossings) > 20:
                    self.recent_crossings.pop(0)

                logger.debug(
                    "Vehicle #%d (%s) crossed line (%s). Total: %d",
                    tid,
                    vtype,
                    direction,
                    self.counts["total_vehicles"],
                )

        return {
            "statistics": dict(self.counts),
            "newly_counted": new_events,
            "recent_crossings": list(self.recent_crossings),
        }

    def get_counts(self) -> Dict[str, int]:
        """Returns snapshot of current counts dictionary."""
        return dict(self.counts)
