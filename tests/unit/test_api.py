"""测试后端 API 端点"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "app"))

from main import app

client = TestClient(app)


class TestRoot:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()


class TestAuth:
    def test_register_missing_fields(self):
        resp = client.post("/api/v1/auth/register", json={"username": "test"})
        assert resp.status_code == 422

    def test_login_invalid_user(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "nonexistent_user_12345",
            "password": "wrong",
        })
        assert resp.status_code == 401


class TestData:
    def test_latest_no_data(self):
        resp = client.get("/api/v1/data/latest?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("success", "empty")

    def test_history_no_params(self):
        resp = client.get("/api/v1/data/history?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "records" in data


class TestML:
    def test_health_score(self):
        resp = client.post("/api/v1/ml/health-score", params={
            "head_angle": 25.0,
            "shoulder_diff": 0.03,
            "hunchback_score": 0.2,
            "body_tilt": 3.0,
            "round_shoulder": 0.12,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert 0 <= data["score"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
