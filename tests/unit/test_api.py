"""测试后端 API 端点（使用 conftest fixtures）"""

import pytest


class TestRoot:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()


class TestAuth:
    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={"username": "test"})
        assert resp.status_code == 422

    def test_login_invalid_user(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "nonexistent_user_12345",
            "password": "wrong",
        })
        assert resp.status_code == 401


class TestData:
    def test_latest_no_data(self, client):
        resp = client.get("/api/v1/data/latest?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("success", "empty")

    def test_history_no_params(self, client):
        resp = client.get("/api/v1/data/history?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "records" in data

    def test_upload_valid_data(self, client):
        payload = {
            "user_id": 1,
            "head_angle": 20.0,
            "shoulder_diff": 0.02,
            "hunchback_score": 0.15,
            "body_tilt": 2.0,
            "round_shoulder": 0.1,
            "posture_label": "normal",
            "confidence": 0.9,
        }
        resp = client.post("/api/v1/data/upload", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_daily_summary(self, client):
        resp = client.get("/api/v1/data/daily-summary?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"


class TestML:
    def test_health_score(self, client):
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


class TestVideo:
    def test_video_status(self, client):
        resp = client.get("/api/v1/video/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "online" in data

    def test_video_live_returns_stream(self, client):
        resp = client.get("/api/v1/video/live.mjpeg")
        assert resp.status_code in (200, 503)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
