"""Integration tests for goals API routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from main import create_app
from database import get_db, Base, engine
from models.db_models import User
from auth import get_password_hash, create_access_token
from datetime import timedelta


# Test database setup - use the same engine as the database module
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        session.commit()  # Commit after creating tables
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(db_session):
    """Create a test client with database override."""
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_client, db_session):
    """Create authentication headers for a test user."""
    # Create test user
    user = User(
        id="test_user_1",
        email="test@example.com",
        hashed_password=get_password_hash("testpass"),  # bcrypt max 72 bytes
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Create access token
    from config.settings import settings
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    return {"Authorization": f"Bearer {access_token}"}


class TestGoalsRoutes:
    """Tests for goals API routes."""

    def test_create_goal_success(self, test_client, auth_headers):
        """Test creating a goal successfully."""
        response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium",
                "description": "Test description"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Goal"
        assert data["target_amount"] == 100000
        assert "id" in data

    def test_create_goal_unauthorized(self, test_client):
        """Test creating a goal without authentication."""
        response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            }
        )

        assert response.status_code == 401

    def test_create_goal_invalid_data(self, test_client, auth_headers):
        """Test creating a goal with invalid data."""
        response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "",  # Empty name
                "target_amount": -100,  # Negative amount
                "timeline_months": 0,  # Invalid timeline
                "priority": "medium"
            },
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_list_goals(self, test_client, auth_headers):
        """Test listing goals."""
        # Create a goal first
        test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )

        response = test_client.get("/api/v1/goals", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert len(data["goals"]) >= 1
        assert data["total_count"] >= 1

    def test_list_goals_unauthorized(self, test_client):
        """Test listing goals without authentication."""
        response = test_client.get("/api/v1/goals")

        assert response.status_code == 401

    def test_get_goal_summary(self, test_client, auth_headers):
        """Test getting goals summary."""
        response = test_client.get("/api/v1/goals/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_goals" in data
        assert "total_target_amount" in data
        assert "overall_completion" in data

    def test_get_goal_by_id(self, test_client, auth_headers):
        """Test getting a specific goal by ID."""
        # Create a goal first
        create_response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )
        goal_id = create_response.json()["id"]

        response = test_client.get(f"/api/v1/goals/{goal_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == goal_id
        assert data["name"] == "Test Goal"

    def test_get_goal_not_found(self, test_client, auth_headers):
        """Test getting a non-existent goal."""
        response = test_client.get("/api/v1/goals/non_existent_id", headers=auth_headers)

        assert response.status_code == 404

    def test_update_goal(self, test_client, auth_headers):
        """Test updating a goal."""
        # Create a goal first
        create_response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )
        goal_id = create_response.json()["id"]

        # Update the goal
        response = test_client.put(
            f"/api/v1/goals/{goal_id}",
            json={
                "name": "Updated Goal",
                "target_amount": 200000
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Goal"
        assert data["target_amount"] == 200000

    def test_update_goal_not_found(self, test_client, auth_headers):
        """Test updating a non-existent goal."""
        response = test_client.put(
            "/api/v1/goals/non_existent_id",
            json={"name": "Updated Goal"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_goal(self, test_client, auth_headers):
        """Test deleting a goal."""
        # Create a goal first
        create_response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )
        goal_id = create_response.json()["id"]

        # Delete the goal
        response = test_client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Goal deleted successfully"
        assert data["goal_id"] == goal_id

    def test_delete_goal_not_found(self, test_client, auth_headers):
        """Test deleting a non-existent goal."""
        response = test_client.delete("/api/v1/goals/non_existent_id", headers=auth_headers)

        assert response.status_code == 404

    def test_update_goal_progress(self, test_client, auth_headers):
        """Test updating goal progress."""
        # Create a goal first
        create_response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )
        goal_id = create_response.json()["id"]

        # Update progress
        response = test_client.post(
            f"/api/v1/goals/{goal_id}/progress",
            json={"amount": 50000},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Goal progress updated successfully"
        assert data["goal"]["current_amount"] == 50000
        assert data["goal"]["completion_percentage"] == 50.0

    def test_update_goal_progress_invalid_amount(self, test_client, auth_headers):
        """Test updating goal progress with invalid amount."""
        # Create a goal first
        create_response = test_client.post(
            "/api/v1/goals",
            json={
                "name": "Test Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "medium"
            },
            headers=auth_headers
        )
        goal_id = create_response.json()["id"]

        # Try to update with negative amount
        response = test_client.post(
            f"/api/v1/goals/{goal_id}/progress",
            json={"amount": -100},
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_get_goal_templates(self, test_client, auth_headers):
        """Test getting goal templates."""
        response = test_client.get("/api/v1/goals/templates", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)

    def test_get_goal_recommendations(self, test_client, auth_headers):
        """Test getting goal recommendations."""
        response = test_client.get("/api/v1/goals/recommendations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_pagination(self, test_client, auth_headers):
        """Test goals pagination."""
        # Create multiple goals
        for i in range(15):
            test_client.post(
                "/api/v1/goals",
                json={
                    "name": f"Goal {i}",
                    "target_amount": 100000 * (i + 1),
                    "timeline_months": 12,
                    "priority": "medium"
                },
                headers=auth_headers
            )

        # Get first page
        response = test_client.get("/api/v1/goals?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 10
        assert data["page"] == 1
        assert data["total_pages"] == 2

        # Get second page
        response = test_client.get("/api/v1/goals?page=2&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 5
        assert data["page"] == 2

    def test_sorting(self, test_client, auth_headers):
        """Test goals sorting."""
        # Create goals with different priorities
        test_client.post(
            "/api/v1/goals",
            json={
                "name": "Low Priority Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "low"
            },
            headers=auth_headers
        )
        test_client.post(
            "/api/v1/goals",
            json={
                "name": "Critical Goal",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "critical"
            },
            headers=auth_headers
        )

        # Get goals sorted by priority
        response = test_client.get("/api/v1/goals?sort_by=priority&sort_order=desc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Critical should come first
        assert data["goals"][0]["priority"] == "critical"
