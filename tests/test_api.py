from fastapi.testclient import TestClient

from app.main import app, get_db
from app.database import Base
from tests.test_database import test_engine, TestSessionLocal
from datetime import datetime

Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Log Ingestion Service is running"
    }


def test_create_log():
    log_data = {
        "timestamp": "2026-08-22T20:00:00+03:00",
        "level": "info",
        "service": "test-service",
        "message": "Test log message",
        "attributes": {
            "environment": "testing",
            "user_id": 123,
        },
    }

    response = client.post("/logs", json=log_data)

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["message"] == "Log stored successfully"


def test_get_logs():
    response = client.get("/logs")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    log = data[0]

    assert "id" in log
    assert "timestamp" in log
    assert "level" in log
    assert "service" in log
    assert "message" in log
    assert "attributes" in log


def test_filter_logs_by_attribute():
    response = client.get(
        "/logs",
        params={"attribute": "environment:testing"},
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["attributes"].get("environment") == "testing"

def test_filter_logs_by_service():
    response = client.get(
        "/logs",
        params={"service": "test-service"},
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["service"] == "test-service"

def test_filter_logs_by_level():
    response = client.get(
        "/logs",
        params={"level": "info"},
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["level"] == "info"

def test_filter_logs_by_message():
    response = client.get(
        "/logs",
        params={"message": "Test log"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) > 0

    for log in data:
        assert "test log" in log["message"].lower()

def test_get_logs_limit():
    response = client.get(
        "/logs",
        params={"limit": 2},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) <= 2

def test_get_logs_offset():
    response_all = client.get("/logs")

    assert response_all.status_code == 200

    all_logs = response_all.json()

    response_offset = client.get(
        "/logs",
        params={"offset": 1},
    )

    assert response_offset.status_code == 200

    offset_logs = response_offset.json()

    if len(all_logs) > 1:
        assert offset_logs[0]["id"] == all_logs[1]["id"]


def test_get_logs_sort_asc():
    response = client.get(
        "/logs",
        params={"sort": "asc"},
    )

    assert response.status_code == 200

    data = response.json()

    timestamps = [log["timestamp"] for log in data]

    assert timestamps == sorted(timestamps)


def test_get_logs_sort_desc():
    response = client.get(
        "/logs",
        params={"sort": "desc"},
    )

    assert response.status_code == 200

    data = response.json()

    timestamps = [log["timestamp"] for log in data]

    assert timestamps == sorted(timestamps, reverse=True)


def test_invalid_sort():
    response = client.get(
        "/logs",
        params={"sort": "wrong"},
    )

    assert response.status_code == 422

def test_invalid_attribute_format():
    response = client.get(
        "/logs",
        params={"attribute": "environment"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Attribute filter must use the format key:value"
    )

def test_filter_logs_by_service_and_level():
    response = client.get(
        "/logs",
        params={
            "service": "test-service",
            "level": "info",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["service"] == "test-service"
        assert log["level"] == "info"

def test_filter_logs_by_service_and_attribute():
    response = client.get(
        "/logs",
        params={
            "service": "test-service",
            "attribute": "environment:testing",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["service"] == "test-service"
        assert log["attributes"].get("environment") == "testing"

def test_filter_logs_by_start_time():
    response = client.get(
        "/logs",
        params={
            "start_time": "2026-08-22T19:00:00+03:00",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
      log_time = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
      start_time = datetime.fromisoformat("2026-08-22T19:00:00+03:00")
      assert log_time >= start_time
def test_filter_logs_by_end_time():
    response = client.get(
        "/logs",
        params={
            "end_time": "2026-08-22T21:00:00+03:00",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for log in data:
        assert log["timestamp"] <= "2026-08-22T21:00:00+03:00"

def test_invalid_time_range():
    response = client.get(
        "/logs",
        params={
            "start_time": "2026-08-23T20:00:00+03:00",
            "end_time": "2026-08-22T20:00:00+03:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_time must be earlier than or equal to end_time"
    )

def test_get_log_by_id():
    response = client.get("/logs")

    assert response.status_code == 200

    logs = response.json()

    assert len(logs) > 0

    log_id = logs[0]["id"]

    response = client.get(f"/logs/{log_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == log_id

def test_get_log_not_found():
    response = client.get("/logs/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Log not found"

def test_delete_log():
    log_data = {
        "timestamp": "2026-08-23T20:00:00+03:00",
        "level": "info",
        "service": "delete-test",
        "message": "Log to be deleted",
        "attributes": {},
    }

    create_response = client.post("/logs", json=log_data)

    assert create_response.status_code == 200

    log_id = create_response.json()["id"]

    delete_response = client.delete(f"/logs/{log_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == log_id

    get_response = client.get(f"/logs/{log_id}")

    assert get_response.status_code == 404

def test_delete_log_not_found():
    response = client.delete("/logs/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Log not found"

def test_delete_old_logs():
    old_log = {
        "timestamp": "2020-01-01T12:00:00+03:00",
        "level": "info",
        "service": "retention-test",
        "message": "Old log",
        "attributes": {},
    }

    recent_log = {
        "timestamp": "2026-08-23T12:00:00+03:00",
        "level": "info",
        "service": "retention-test",
        "message": "Recent log",
        "attributes": {},
    }

    old_response = client.post("/logs", json=old_log)
    recent_response = client.post("/logs", json=recent_log)

    assert old_response.status_code == 200
    assert recent_response.status_code == 200

    old_id = old_response.json()["id"]
    recent_id = recent_response.json()["id"]

    response = client.delete(
        "/logs/retention",
        params={"days": 30},
    )

    assert response.status_code == 200
    assert response.json()["deleted"] >= 1

    old_check = client.get(f"/logs/{old_id}")
    recent_check = client.get(f"/logs/{recent_id}")

    assert old_check.status_code == 404
    assert recent_check.status_code == 200

def test_get_log_stats():
    logs = [
        {
            "timestamp": "2026-08-23T10:00:00+03:00",
            "level": "info",
            "service": "stats-test",
            "message": "Info log",
            "attributes": {},
        },
        {
            "timestamp": "2026-08-23T11:00:00+03:00",
            "level": "error",
            "service": "stats-test",
            "message": "Error log",
            "attributes": {},
        },
        {
            "timestamp": "2026-08-23T12:00:00+03:00",
            "level": "info",
            "service": "stats-test",
            "message": "Another info log",
            "attributes": {},
        },
    ]

    for log in logs:
        response = client.post("/logs", json=log)
        assert response.status_code == 200

    response = client.get(
        "/logs/stats",
        params={"start_time": "2026-08-23T09:00:00+03:00"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 3
    assert data["by_level"]["info"] >= 2
    assert data["by_level"]["error"] >= 1
    assert data["by_service"]["stats-test"] >= 3


def test_invalid_stats_time_range():
    response = client.get(
        "/logs/stats",
        params={
            "start_time": "2026-08-23T20:00:00+03:00",
            "end_time": "2026-08-22T20:00:00+03:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_time must be earlier than or equal to end_time"
    )

def test_invalid_attribute_empty_key():
    response = client.get(
        "/logs",
        params={"attribute": ":testing"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Attribute filter key and value cannot be empty"
    )


def test_invalid_attribute_empty_value():
    response = client.get(
        "/logs",
        params={"attribute": "environment:"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Attribute filter key and value cannot be empty"
    )
