import json
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app


class TestTrafficAPI(unittest.TestCase):
    """Integration test suite for Flask REST API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("ai_model", data)
        self.assertIn("worker", data)

    def test_traffic_endpoints(self):
        # Combined
        resp = self.client.get("/api/traffic")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("vehicle_counts", data)
        self.assertIn("density", data)
        self.assertIn("speed", data)
        self.assertIn("congestion", data)

        # Counts
        resp_counts = self.client.get("/api/traffic/counts")
        self.assertEqual(resp_counts.status_code, 200)
        counts_data = resp_counts.get_json()
        self.assertIn("counts", counts_data)

        # Density
        resp_density = self.client.get("/api/traffic/density")
        self.assertEqual(resp_density.status_code, 200)
        self.assertIn("density", resp_density.get_json())

        # Speed
        resp_speed = self.client.get("/api/traffic/speed")
        self.assertEqual(resp_speed.status_code, 200)
        self.assertIn("speed", resp_speed.get_json())

        # Congestion
        resp_cong = self.client.get("/api/traffic/congestion")
        self.assertEqual(resp_cong.status_code, 200)
        self.assertIn("congestion", resp_cong.get_json())

    def test_cameras_endpoints(self):
        # List cameras
        resp = self.client.get("/api/cameras")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("cameras", data)
        self.assertGreaterEqual(len(data["cameras"]), 1)

        # Register new camera
        new_cam_payload = {
            "name": "Test Highway Camera",
            "location": "Route 66 - Overpass",
            "stream_source": "0",
            "road_capacity": 20,
            "latitude": 40.7300,
            "longitude": -73.9950,
        }
        create_resp = self.client.post(
            "/api/cameras",
            data=json.dumps(new_cam_payload),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 201)
        created_data = create_resp.get_json()
        cam_id = created_data["camera"]["id"]

        # Configure camera
        config_payload = {
            "counting_line": [[150, 400], [1100, 400]],
            "roi_polygon": [[100, 200], [1150, 200], [1200, 600], [50, 600]],
            "road_capacity": 18,
        }
        conf_resp = self.client.post(
            f"/api/cameras/{cam_id}/configure",
            data=json.dumps(config_payload),
            content_type="application/json",
        )
        self.assertEqual(conf_resp.status_code, 200)

    def test_analytics_and_history(self):
        resp_analytics = self.client.get("/api/analytics")
        self.assertEqual(resp_analytics.status_code, 200)
        data = resp_analytics.get_json()
        self.assertIn("summary", data)
        self.assertIn("hourly_trends", data)

        resp_hist = self.client.get("/api/history?limit=10")
        self.assertEqual(resp_hist.status_code, 200)
        self.assertIn("history", resp_hist.get_json())

    def test_detection_controls(self):
        # Stop detection
        stop_resp = self.client.post("/api/detection/stop")
        self.assertEqual(stop_resp.status_code, 200)

        # Start with invalid source should return 400
        invalid_start = self.client.post(
            "/api/detection/start",
            data=json.dumps({"camera_id": "cam-01", "source": "non_existent_stream.xyz"}),
            content_type="application/json",
        )
        self.assertEqual(invalid_start.status_code, 400)


if __name__ == "__main__":
    unittest.main()
