"""FastAPI application entry point for micro-investing assistant."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.settings import settings
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
from config.model_metadata import MODEL_INFO, AUDIT_LOGGER
from services.recommendation_service import RecommendationService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Log request
        logger.info(f"[{request_id}] {request.method} {request.url.path}")

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Log response time
        process_time = time.time() - start_time
        logger.info(f"[{request_id}] Completed in {process_time*1000:.2f}ms")

        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for global exception handling."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())

        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"[{request_id}] Unhandled exception: {str(e)}", exc_info=True)
            AUDIT_LOGGER.log_validation_error(
                request_id=request_id,
                error_type=type(e).__name__,
                error_details=str(e)
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id}
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown."""

    # Startup
    logger.info("=" * 60)
    logger.info("Micro-Investing Assistant API - Starting")
    logger.info("=" * 60)

    # Load ML artifacts
    logger.info("Loading ML artifacts...")
    try:
        from models.ml_pipeline import MicroInvestmentAssistant
        assistant = MicroInvestmentAssistant(artifacts_dir=settings.artifacts_dir)
        model_info = assistant.get_model_info()
        logger.info(f"ML Model: {model_info['model_name']} v{model_info['version']}")
        logger.info(f"Clusters: {model_info['segment_labels']}")
        logger.info(f"Features: {model_info['features']}")
    except Exception as e:
        logger.error(f"Failed to load ML artifacts: {e}")
        raise

    # Log model metadata
    logger.info(f"Model Version: {MODEL_INFO.version}")
    logger.info(f"Training Date: {MODEL_INFO.training_date}")
    logger.info(f"Silhouette Score: {MODEL_INFO.silhouette_score}")

    # Initialize services
    logger.info("Initializing recommendation service...")
    RecommendationService()
    logger.info("Recommendation service initialized")

    logger.info("=" * 60)
    logger.info("Server started successfully")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Shutting down server...")
    logger.info("Audit logs exported to: audit_trail.json")

    # Export audit trail
    audit_json = AUDIT_LOGGER.export_audit_trail()
    with open("audit_trail.json", "w") as f:
        f.write(audit_json)
    logger.info(f"Audit trail exported ({len(AUDIT_LOGGER.logs)} entries)")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Micro-Investing Assistant API",
        description="Beginner-safe micro-investing recommendations using behavioral clustering. "
        "This is an educational tool, not SEBI-registered investment advice.",
        version="2.0.0",
        lifespan=lifespan
    )

    # Middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(api_router, prefix="/api/v1", tags=["Main API"])
    app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
    app.include_router(goals_router, prefix="/api/v1", tags=["Goals"])
    app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(system_router, prefix="/api/v1", tags=["System"])
    app.include_router(profile_router, prefix="/api/v1", tags=["User Profile"])
    app.include_router(transactions_router, prefix="/api/v1", tags=["Transactions"])
    app.include_router(sips_router, prefix="/api/v1", tags=["SIP Management"])
    app.include_router(portfolio_router, prefix="/api/v1", tags=["Portfolio"])
    app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])

    @app.get("/")
    async def root():
        return {
            "service": "Micro-Investing Assistant",
            "status": "running",
            "version": "2.0.0",
            "regulatory_notice": "Educational tool only - Not SEBI registered advisory"
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": time.time()
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False  # Disable reload in production
    )
