from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app import activities, app, unregister_from_activity


@pytest.fixture
def activity():
    activity = {
        "description": "Chess",
        "schedule": "Friday",
        "max_participants": 4,
        "participants": ["student+chess@example.com", "other@example.com", "student+chess@example.com"],
    }
    with patch.dict(activities, {"Chess Club": activity}, clear=True):
        yield activity


@pytest.fixture
def client(activity):
    with TestClient(app) as client:
        yield client


def test_root_redirects_to_index(client):
    # Arrange: the activity and client are prepared by fixtures.

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_details(client, activity):
    # Arrange: the activity and client are prepared by fixtures.

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"Chess Club": activity}


def test_signup_list_and_unregister(client):
    # Arrange
    email = "new+chess@example.com"
    url = "/activities/Chess%20Club/signup"

    # Act
    signup = client.post(url, params={"email": email})
    after_signup = client.get("/activities").json()["Chess Club"]["participants"]
    unregister = client.delete(url, params={"email": email})
    after_unregister = client.get("/activities").json()["Chess Club"]["participants"]

    # Assert
    assert signup.status_code == 200
    assert signup.json() == {"message": f"Signed up {email} for Chess Club"}
    assert after_signup == [
        "student+chess@example.com", "other@example.com", "student+chess@example.com", email
    ]
    assert unregister.status_code == 200
    assert unregister.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert after_unregister == [
        "student+chess@example.com", "other@example.com", "student+chess@example.com"
    ]


def test_signup_unknown_activity_does_not_change_participants(client, activity):
    # Arrange
    before = activity["participants"].copy()

    # Act
    response = client.post("/activities/Unknown/signup", params={"email": "new@example.com"})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert activity["participants"] == before


def test_duplicate_signup_does_not_change_participants(client, activity):
    # Arrange
    before = activity["participants"].copy()

    # Act
    response = client.post(
        "/activities/Chess%20Club/signup", params={"email": "student+chess@example.com"}
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert activity["participants"] == before


@pytest.mark.parametrize("method", ["post", "delete"])
def test_missing_email_is_rejected_without_changing_participants(client, activity, method):
    # Arrange
    before = activity["participants"].copy()

    # Act
    response = getattr(client, method)("/activities/Chess%20Club/signup")

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]
    assert activity["participants"] == before


def test_unregister_removes_all_matching_entries(client, activity):
    # Arrange: the activity and client are prepared by fixtures.

    # Act
    response = client.delete(
        "/activities/Chess%20Club/signup", params={"email": "student+chess@example.com"}
    )
    listed_participants = client.get("/activities").json()["Chess Club"]["participants"]

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": "Unregistered student+chess@example.com from Chess Club"
    }
    assert activity["participants"] == ["other@example.com"]
    assert listed_participants == ["other@example.com"]


def test_missing_activity_or_participant_returns_404(client, activity):
    # Arrange
    before = activity["participants"].copy()

    # Act
    missing_activity = client.delete("/activities/Unknown/signup", params={"email": "other@example.com"})
    missing_participant = client.delete("/activities/Chess%20Club/signup", params={"email": "missing@example.com"})

    # Assert
    assert missing_activity.status_code == 404
    assert missing_activity.json() == {"detail": "Activity not found"}
    assert missing_participant.status_code == 404
    assert missing_participant.json() == {"detail": "Student not signed up for this activity"}
    assert activity["participants"] == before


def test_unregister_mutates_existing_participant_list(activity):
    # Arrange
    participants = activity["participants"]

    # Act
    result = unregister_from_activity("Chess Club", "student+chess@example.com")

    # Assert
    assert result == {"message": "Unregistered student+chess@example.com from Chess Club"}
    assert activity["participants"] is participants
    assert participants == ["other@example.com"]


def test_unregister_missing_participant_raises_without_mutating_list(activity):
    # Arrange
    participants = activity["participants"]
    before = participants.copy()

    # Act
    with pytest.raises(HTTPException) as raised:
        unregister_from_activity("Chess Club", "missing@example.com")

    # Assert
    assert raised.value.status_code == 404
    assert raised.value.detail == "Student not signed up for this activity"
    assert activity["participants"] is participants
    assert participants == before
