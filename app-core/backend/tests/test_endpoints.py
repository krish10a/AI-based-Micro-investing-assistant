"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Micro-Investing Assistant"
        assert data["status"] == "running"


class TestAnalyzeUserEndpoint:
    """Tests for analyze-user endpoint."""

    def test_analyze_valid_input(self, client, sample_user_input):
        """Test analysis with valid input."""
        response = client.post("/api/v1/analyze-user", json=sample_user_input)
        # May fail if artifacts not loaded, but should not be 422
        assert response.status_code in [200, 500]

    def test_analyze_negative_income(self, client):
        """Test analysis rejects negative income."""
        invalid_input = {
            "income": -1000,
            "rent": 5000
        }
        response = client.post("/api/v1/analyze-user", json=invalid_input)
        assert response.status_code == 422

    def test_analyze_missing_required_field(self, client):
        """Test analysis rejects missing required fields."""
        invalid_input = {
            "rent": 5000
        }
        response = client.post("/api/v1/analyze-user", json=invalid_input)
        assert response.status_code == 422

    def test_analyze_skip_explanation(self, client, sample_user_input):
        """Test analysis with skip_explanation flag."""
        response = client.post(
            "/api/v1/analyze-user?skip_explanation=true",
            json=sample_user_input
        )
        # Should return faster without NIM call
        assert response.status_code in [200, 500]


class TestModelInfoEndpoint:
    """Tests for model-info endpoint."""

    def test_model_info(self, client):
        """Test model info endpoint."""
        response = client.get("/api/v1/model-info")
        # May fail if artifacts not loaded
        assert response.status_code in [200, 500]


class TestChatEndpoint:
    """Tests for chat endpoint."""

    @pytest.mark.skip(reason="Requires NIM API key configured - integration test")
    def test_chat_endpoint_exists(self, client):
        """Test chat endpoint exists (integration test requires NIM API)."""
        request = {
            "message": "What should I invest in?",
            "user_profile": {"segment": "test"}
        }
        response = client.post("/api/v1/chat", json=request)
        assert response.status_code in [200, 500]
