"""Script to initialize goal templates in the database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models.db_models import GoalTemplate, PriorityEnum
import uuid

def init_goal_templates():
    """Initialize goal templates in the database."""
    db = SessionLocal()

    try:
        # Check if templates already exist
        existing = db.query(GoalTemplate).count()
        if existing > 0:
            print(f"Found {existing} existing templates. Skipping initialization.")
            return

        templates = [
            {
                "id": str(uuid.uuid4()),
                "name": "Emergency Fund",
                "category": "Retirement",
                "description": "Build a 6-month emergency fund for financial security",
                "default_target_amount": 300000,
                "default_timeline_months": 12,
                "default_priority": PriorityEnum.CRITICAL,
                "suggested_monthly_contribution": 25000,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Dream Vacation",
                "category": "Travel",
                "description": "Save for your dream vacation to explore the world",
                "default_target_amount": 200000,
                "default_timeline_months": 24,
                "default_priority": PriorityEnum.LOW,
                "suggested_monthly_contribution": 8333,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Home Down Payment",
                "category": "Home Purchase",
                "description": "Save for down payment on your dream home",
                "default_target_amount": 1000000,
                "default_timeline_months": 60,
                "default_priority": PriorityEnum.HIGH,
                "suggested_monthly_contribution": 16667,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Retirement Corpus",
                "category": "Retirement",
                "description": "Build a comfortable retirement corpus",
                "default_target_amount": 10000000,
                "default_timeline_months": 360,
                "default_priority": PriorityEnum.HIGH,
                "suggested_monthly_contribution": 27778,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Child's Education",
                "category": "Child Education",
                "description": "Save for your child's higher education",
                "default_target_amount": 2000000,
                "default_timeline_months": 180,
                "default_priority": PriorityEnum.HIGH,
                "suggested_monthly_contribution": 11111,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Wealth Building",
                "category": "Wealth Building",
                "description": "Build wealth through systematic investments",
                "default_target_amount": 5000000,
                "default_timeline_months": 120,
                "default_priority": PriorityEnum.MEDIUM,
                "suggested_monthly_contribution": 41667,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Skill Development",
                "category": "Education Upskilling",
                "description": "Invest in your professional growth and skills",
                "default_target_amount": 100000,
                "default_timeline_months": 12,
                "default_priority": PriorityEnum.MEDIUM,
                "suggested_monthly_contribution": 8333,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "New Car",
                "category": "Wealth Building",
                "description": "Save for your dream car",
                "default_target_amount": 800000,
                "default_timeline_months": 36,
                "default_priority": PriorityEnum.MEDIUM,
                "suggested_monthly_contribution": 22222,
            },
        ]

        for template_data in templates:
            template = GoalTemplate(**template_data)
            db.add(template)

        db.commit()
        print(f"Successfully initialized {len(templates)} goal templates")

    except Exception as e:
        print(f"Error initializing goal templates: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Initializing goal templates...")
    init_goal_templates()
    print("Done!")
