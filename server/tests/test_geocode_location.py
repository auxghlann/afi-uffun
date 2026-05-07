import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure 'app' package is importable from the server root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the node under test at module level so all tests can use it
from app.services.ai.nodes import geocode_location_node, geo_router_node



# ---------------------------------------------------------------------------
# Helper: build a minimal EmergencyState dict for testing
# ---------------------------------------------------------------------------
def _make_state(location_name: str = "", gps_lat: float = 14.5995, gps_lon: float = 120.9842) -> dict:
    return {
        "messages": [],
        "location": {"latitude": gps_lat, "longitude": gps_lon},
        "extracted_details": {
            "location_name": location_name,
            "location_details": "some details",
            "emergency_types": "Fire",
            "severity": "High",
            "people_affected": "many",
            "is_ongoing": "True",
            "summary": "Test emergency",
        },
        "resolved_location": {},
        "routed_hotlines": [],
        "pending_review": False,
        "review_status": "pending",
        "review_notes": "",
        "status": "gathering_info",
    }


# ---------------------------------------------------------------------------
# Fake Nominatim responses
# ---------------------------------------------------------------------------
_NOMINATIM_HIT = [{"lat": "17.6134", "lon": "121.7269", "display_name": "SM Tuguegarao, Cagayan"}]
_NOMINATIM_MISS = []  # empty list = place not found


class TestGeocodeLocationNode(unittest.TestCase):
    """Tests for geocode_location_node in nodes.py"""

    # ------------------------------------------------------------------
    # 1. Successful geocoding — explicit location name resolves to coords
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_explicit_location_geocoded(self, mock_get):
        """When location_name is set and Nominatim returns a result,
        resolved_location should use the geocoded coords with source='extracted'."""
        mock_response = MagicMock()
        mock_response.json.return_value = _NOMINATIM_HIT
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from app.services.ai.nodes import geocode_location_node

        state = _make_state(location_name="SM Mall, Tuguegarao City")
        result = geocode_location_node(state)

        resolved = result["resolved_location"]
        self.assertAlmostEqual(resolved["latitude"], 17.6134, places=4)
        self.assertAlmostEqual(resolved["longitude"], 121.7269, places=4)
        self.assertEqual(resolved["source"], "extracted")

    # ------------------------------------------------------------------
    # 2. Empty location_name — must fall back to GPS
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_empty_location_name_falls_back_to_gps(self, mock_get):
        """When no location_name is in extracted_details, skip Nominatim
        and use the caller's GPS coordinates."""
        state = _make_state(location_name="", gps_lat=14.5995, gps_lon=120.9842)
        result = geocode_location_node(state)

        # Nominatim must NOT be called
        mock_get.assert_not_called()

        resolved = result["resolved_location"]
        self.assertAlmostEqual(resolved["latitude"], 14.5995, places=4)
        self.assertAlmostEqual(resolved["longitude"], 120.9842, places=4)
        self.assertEqual(resolved["source"], "gps")

    # ------------------------------------------------------------------
    # 3. Nominatim returns no results — fall back to GPS
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_nominatim_no_results_falls_back_to_gps(self, mock_get):
        """When Nominatim returns an empty list, fall back to GPS silently."""
        mock_response = MagicMock()
        mock_response.json.return_value = _NOMINATIM_MISS
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from app.services.ai.nodes import geocode_location_node

        state = _make_state(location_name="Nonexistent Barangay XYZ", gps_lat=14.0, gps_lon=121.0)
        result = geocode_location_node(state)

        resolved = result["resolved_location"]
        self.assertAlmostEqual(resolved["latitude"], 14.0, places=4)
        self.assertAlmostEqual(resolved["longitude"], 121.0, places=4)
        self.assertEqual(resolved["source"], "gps")

    # ------------------------------------------------------------------
    # 4. Nominatim raises a network error — fall back to GPS
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_network_error_falls_back_to_gps(self, mock_get):
        """When Nominatim raises any exception, fall back to GPS silently."""
        import httpx
        mock_get.side_effect = httpx.RequestError("Connection timeout")

        from app.services.ai.nodes import geocode_location_node

        state = _make_state(location_name="Burgos Street, Manila", gps_lat=13.0, gps_lon=122.5)
        result = geocode_location_node(state)

        resolved = result["resolved_location"]
        self.assertAlmostEqual(resolved["latitude"], 13.0, places=4)
        self.assertAlmostEqual(resolved["longitude"], 122.5, places=4)
        self.assertEqual(resolved["source"], "gps")

    # ------------------------------------------------------------------
    # 5. Nominatim called with correct query params
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_nominatim_called_with_correct_params(self, mock_get):
        """Nominatim must be called with countrycodes=ph, format=json, limit=1."""
        mock_response = MagicMock()
        mock_response.json.return_value = _NOMINATIM_HIT
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from app.services.ai.nodes import geocode_location_node

        state = _make_state(location_name="Rizal Park, Manila")
        geocode_location_node(state)

        # Check the URL that was called
        call_args = mock_get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        params = call_args[1].get("params", {}) if call_args[1] else {}

        self.assertIn("nominatim.openstreetmap.org", url)
        self.assertEqual(params.get("format"), "json")
        self.assertEqual(params.get("limit"), 1)
        self.assertEqual(params.get("countrycodes"), "ph")
        self.assertIn("Rizal Park, Manila", params.get("q", ""))

    # ------------------------------------------------------------------
    # 6. location_name with only whitespace treated as empty
    # ------------------------------------------------------------------
    @patch("app.services.ai.nodes.httpx.get")
    def test_whitespace_location_name_treated_as_empty(self, mock_get):
        """A location_name that is only whitespace should skip geocoding."""
        state = _make_state(location_name="   ", gps_lat=16.0, gps_lon=120.5)
        result = geocode_location_node(state)

        mock_get.assert_not_called()
        self.assertEqual(result["resolved_location"]["source"], "gps")

    # ------------------------------------------------------------------
    # 7. geo_router_node uses resolved_location, not raw GPS
    # ------------------------------------------------------------------
    def test_geo_router_uses_resolved_location(self):
        """geo_router_node should read from resolved_location, not location."""
        state = _make_state(location_name="", gps_lat=99.0, gps_lon=99.0)  # garbage GPS
        state["resolved_location"] = {"latitude": 17.6134, "longitude": 121.7269, "source": "extracted"}
        state["extracted_details"]["emergency_types"] = "Fire"

        mock_hotline = MagicMock()
        mock_hotline.id = 1
        mock_hotline.name = "BFP Tuguegarao"
        mock_hotline.type = "Fire"
        mock_hotline.lat = 17.6130
        mock_hotline.lon = 121.7265
        mock_hotline.contact = "09171234567"

        # SessionLocal is imported lazily inside geo_router_node — patch at source module
        with patch("app.database.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_hotline]

            result = geo_router_node(state)

        hotlines = result["routed_hotlines"]
        self.assertEqual(len(hotlines), 1)
        self.assertEqual(hotlines[0]["name"], "BFP Tuguegarao")
        # Distance must be calculated from resolved coords (17.6134, 121.7269), not GPS (99, 99)
        self.assertLess(hotlines[0]["distance_km"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
