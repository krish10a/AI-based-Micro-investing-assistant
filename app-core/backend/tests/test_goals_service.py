"""Unit tests for goals service."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import Base, User, Goal, PriorityEnum, GoalStatusEnum
from services.goals_service import GoalsService
from models.goals import GoalCreate, GoalUpdate


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        id="test_user_1",
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def goals_service(db_session):
    """Create a goals service instance."""
    return GoalsService(db_session)


class TestGoalsService:
    """Tests for GoalsService."""

    def test_create_goal(self, goals_service, test_user):
        """Test creating a new goal."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM,
            description="Test description"
        )

        goal = goals_service.create_goal(test_user.id, goal_data)

        assert goal.id is not None
        assert goal.name == "Test Goal"
        assert goal.target_amount == 100000
        assert goal.current_amount == 0
        assert goal.completion_percentage == 0
        assert goal.achieved is False
        assert goal.monthly_suggested_contribution > 0

    def test_create_goal_validates_timeline(self, goals_service, test_user):
        """Test that creating a goal with invalid timeline raises error."""
        # Pydantic validates timeline_months > 0, so this will raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            GoalCreate(
                name="Test Goal",
                target_amount=100000,
                timeline_months=0,
                priority=PriorityEnum.MEDIUM
            )

    def test_get_goal(self, goals_service, test_user):
        """Test retrieving a goal by ID."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        retrieved_goal = goals_service.get_goal(created_goal.id, test_user.id)

        assert retrieved_goal is not None
        assert retrieved_goal.id == created_goal.id
        assert retrieved_goal.name == "Test Goal"

    def test_get_goal_not_found(self, goals_service, test_user):
        """Test retrieving a non-existent goal."""
        goal = goals_service.get_goal("non_existent_id", test_user.id)
        assert goal is None

    def test_get_goal_wrong_user(self, goals_service, test_user):
        """Test that a user cannot access another user's goal."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        # Try to access with different user ID
        goal = goals_service.get_goal(created_goal.id, "different_user_id")
        assert goal is None

    def test_get_all_goals(self, goals_service, test_user):
        """Test retrieving all goals for a user."""
        # Create multiple goals
        for i in range(3):
            goal_data = GoalCreate(
                name=f"Goal {i}",
                target_amount=100000 * (i + 1),
                timeline_months=12,
                priority=PriorityEnum.MEDIUM
            )
            goals_service.create_goal(test_user.id, goal_data)

        goals = goals_service.get_all_goals(test_user.id)

        assert len(goals) == 3
        # Note: GoalResponse doesn't include user_id, so we verify by count only

    def test_update_goal(self, goals_service, test_user):
        """Test updating a goal."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        update_data = GoalUpdate(
            name="Updated Goal",
            target_amount=200000
        )

        updated_goal = goals_service.update_goal(created_goal.id, test_user.id, update_data)

        assert updated_goal.name == "Updated Goal"
        assert updated_goal.target_amount == 200000

    def test_update_goal_not_found(self, goals_service, test_user):
        """Test updating a non-existent goal."""
        update_data = GoalUpdate(name="Updated Goal")
        goal = goals_service.update_goal("non_existent_id", test_user.id, update_data)
        assert goal is None

    def test_delete_goal(self, goals_service, test_user):
        """Test deleting a goal."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        deleted = goals_service.delete_goal(created_goal.id, test_user.id)

        assert deleted is True

        # Verify goal is deleted
        goal = goals_service.get_goal(created_goal.id, test_user.id)
        assert goal is None

    def test_delete_goal_not_found(self, goals_service, test_user):
        """Test deleting a non-existent goal."""
        deleted = goals_service.delete_goal("non_existent_id", test_user.id)
        assert deleted is False

    def test_update_goal_progress(self, goals_service, test_user):
        """Test updating goal progress."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        updated_goal = goals_service.update_goal_progress(created_goal.id, test_user.id, 50000)

        assert updated_goal.current_amount == 50000
        assert updated_goal.completion_percentage == 50.0
        assert updated_goal.achieved is False

    def test_update_goal_progress_achieved(self, goals_service, test_user):
        """Test that goal is marked as achieved when 100% complete."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        updated_goal = goals_service.update_goal_progress(created_goal.id, test_user.id, 100000)

        assert updated_goal.current_amount == 100000
        assert updated_goal.completion_percentage == 100.0
        assert updated_goal.achieved is True
        assert updated_goal.status == GoalStatusEnum.COMPLETED

    def test_update_goal_progress_invalid_amount(self, goals_service, test_user):
        """Test that updating with invalid amount raises error."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        created_goal = goals_service.create_goal(test_user.id, goal_data)

        with pytest.raises(ValueError, match="Amount must be positive"):
            goals_service.update_goal_progress(created_goal.id, test_user.id, -100)

    def test_get_goals_summary(self, goals_service, test_user):
        """Test getting goals summary."""
        # Create multiple goals
        for i in range(3):
            goal_data = GoalCreate(
                name=f"Goal {i}",
                target_amount=100000 * (i + 1),
                timeline_months=12,
                priority=PriorityEnum.MEDIUM
            )
            goals_service.create_goal(test_user.id, goal_data)

        summary = goals_service.get_goals_summary(test_user.id)

        assert summary["total_goals"] == 3
        assert summary["total_target_amount"] == 600000
        assert summary["total_current_amount"] == 0
        assert summary["overall_completion"] == 0
        assert summary["achieved_count"] == 0
        assert summary["pending_count"] == 3

    def test_calculate_monthly_contribution(self, goals_service):
        """Test monthly contribution calculation."""
        # Test with 12% expected return
        contribution = goals_service._calculate_monthly_contribution(100000, 12, 0.12)
        assert contribution > 0
        assert contribution < 100000  # Should be less than target due to compounding

        # Test with zero return
        contribution = goals_service._calculate_monthly_contribution(100000, 12, 0)
        assert contribution == pytest.approx(8333.33, rel=0.01)  # 100000 / 12

    def test_calculate_goal_status(self, goals_service, test_user, db_session):
        """Test goal status calculation."""
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        goal_response = goals_service.create_goal(test_user.id, goal_data)

        # Get the actual database model
        from models.db_models import Goal
        goal = db_session.query(Goal).filter(Goal.id == goal_response.id).first()

        # Test on-track status (set created_at to 6 months ago with 50% progress)
        from datetime import timedelta
        goal.created_at = datetime.utcnow() - timedelta(days=180)  # 6 months ago
        goal.current_amount = 50000  # 50% progress
        goal.completion_percentage = 50.0
        status = goals_service._calculate_goal_status(goal)
        assert status == GoalStatusEnum.ON_TRACK

        # Test ahead status (set created_at to 6 months ago with 70% progress)
        goal.current_amount = 70000  # 70% progress
        goal.completion_percentage = 70.0
        status = goals_service._calculate_goal_status(goal)
        assert status == GoalStatusEnum.AHEAD

        # Test behind status (set created_at to 6 months ago with 10% progress)
        goal.current_amount = 10000  # 10% progress
        goal.completion_percentage = 10.0
        status = goals_service._calculate_goal_status(goal)
        assert status == GoalStatusEnum.BEHIND

    def test_get_goal_templates(self, goals_service):
        """Test getting goal templates."""
        templates = goals_service.get_goal_templates()
        assert isinstance(templates, list)

    def test_get_goal_recommendations(self, goals_service, test_user):
        """Test getting goal recommendations."""
        # Create a goal
        goal_data = GoalCreate(
            name="Test Goal",
            target_amount=100000,
            timeline_months=12,
            priority=PriorityEnum.MEDIUM
        )
        goals_service.create_goal(test_user.id, goal_data)

        recommendations = goals_service.get_goal_recommendations(test_user.id)

        assert isinstance(recommendations, list)
