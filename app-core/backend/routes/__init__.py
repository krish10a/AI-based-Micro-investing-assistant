# Routes package
from routes.api import router as api_router
from routes.analytics import router as analytics_router
from routes.goals import router as goals_router
from routes.auth import router as auth_router
from routes.system import router as system_router
from routes.profile import router as profile_router
from routes.transactions import router as transactions_router
from routes.sips import router as sips_router
from routes.portfolio import router as portfolio_router
from routes.reports import router as reports_router

__all__ = [
    "api_router",
    "analytics_router",
    "goals_router",
    "auth_router",
    "system_router",
    "profile_router",
    "transactions_router",
    "sips_router",
    "portfolio_router",
    "reports_router",
]
