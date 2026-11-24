import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app import activities, app


class UnregisterTests(unittest.TestCase):
    def setUp(self):
        self.activity = {
            "description": "Chess",
            "schedule": "Friday",
            "max_participants": 4,
            "participants": ["student+chess@example.com", "other@example.com", "student+chess@example.com"],
        }
        self.activities_patch = patch.dict(activities, {"Chess Club": self.activity}, clear=True)
        self.activities_patch.start()
        self.addCleanup(self.activities_patch.stop)
        self.client = TestClient(app)

    def test_unregister_removes_all_matching_entries(self):
        response = self.client.delete(
            "/activities/Chess%20Club/signup", params={"email": "student+chess@example.com"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.activity["participants"], ["other@example.com"])
        self.assertEqual(self.client.get("/activities").json()["Chess Club"]["participants"], ["other@example.com"])

    def test_missing_activity_or_participant_returns_404(self):
        missing_activity = self.client.delete("/activities/Unknown/signup", params={"email": "other@example.com"})
        missing_participant = self.client.delete("/activities/Chess%20Club/signup", params={"email": "missing@example.com"})

        self.assertEqual(missing_activity.status_code, 404)
        self.assertEqual(missing_participant.status_code, 404)
        self.assertEqual(len(self.activity["participants"]), 3)


if __name__ == "__main__":
    unittest.main()
