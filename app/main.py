"""
EduTrack - Application Entry Point

Run:
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_client

logger = logging.getLogger("edutrack")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Startup: warm up DB pool and verify connectivity.
    Shutdown: dispose the engine cleanly.
    """
    import logging as std_logging
    from app.core.logging import setup_logging

    json_logs = settings.ENVIRONMENT != "development"
    setup_logging(
        log_level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO",
        json_output=json_logs,
    )
    app_logger = std_logging.getLogger("edutrack")

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        app_logger.info("Database connection OK")
    except Exception as exc:
        app_logger.warning("Database not reachable at startup: %s", exc)

    yield

    await engine.dispose()


app = FastAPI(
    title="EduTrack API",
    description="Unified academic assessment platform - REST + WebSocket API",
    version="1.0.0",
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTPException with the standard API error envelope."""
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(exc.detail))
    else:
        code = "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 422 validation errors with a stable response shape."""
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected exceptions and return a generic 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.admin.analytics import router as admin_analytics_router  # noqa: E402
from app.api.v1.admin.curriculum import router as admin_curriculum_router  # noqa: E402
from app.api.v1.admin.groups import router as admin_groups_router  # noqa: E402
from app.api.v1.admin.users import router as admin_users_router  # noqa: E402
from app.api.v1.student.analytics import router as student_analytics_router  # noqa: E402
from app.api.v1.student.results import router as student_results_router  # noqa: E402
from app.api.v1.student.take import router as student_take_router  # noqa: E402
from app.api.v1.teacher.analytics import router as teacher_analytics_router  # noqa: E402
from app.api.v1.teacher.assessments import router as teacher_assessments_router  # noqa: E402
from app.api.v1.teacher.curriculum import router as teacher_curriculum_router  # noqa: E402
from app.api.v1.teacher.questions import router as teacher_questions_router  # noqa: E402
from app.api.v1.teacher.results import router as teacher_results_router  # noqa: E402
from app.api.websocket.proctoring import router as ws_proctoring_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])

app.include_router(admin_users_router, prefix="/api/v1/admin/users", tags=["Admin - Users"])
app.include_router(admin_groups_router, prefix="/api/v1/admin/groups", tags=["Admin - Groups"])
app.include_router(admin_curriculum_router, prefix="/api/v1/admin/curriculum", tags=["Admin - Curriculum"])
app.include_router(admin_analytics_router, prefix="/api/v1/admin", tags=["Admin - Analytics"])

app.include_router(
    teacher_assessments_router,
    prefix="/api/v1/teacher/assessments",
    tags=["Teacher - Assessments"],
)
app.include_router(teacher_curriculum_router, prefix="/api/v1/teacher", tags=["Teacher - Curriculum"])
app.include_router(teacher_questions_router, prefix="/api/v1/teacher", tags=["Teacher - Questions"])
app.include_router(teacher_results_router, prefix="/api/v1/teacher", tags=["Teacher - Results"])
app.include_router(teacher_analytics_router, prefix="/api/v1/teacher", tags=["Teacher - Analytics"])

app.include_router(student_take_router, prefix="/api/v1/student", tags=["Student - Take Assessment"])
app.include_router(student_results_router, prefix="/api/v1/student/results", tags=["Student - Results"])
app.include_router(student_analytics_router, prefix="/api/v1/student/analytics", tags=["Student - Analytics"])

app.include_router(ws_proctoring_router, tags=["WebSocket - Proctoring"])


@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    return {
        "name": "EduTrack API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    db_ok = False
    redis_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("Database readiness check failed: %s", exc)

    try:
        redis_ok = bool(await redis_client.ping())
    except Exception as exc:
        logger.warning("Redis readiness check failed: %s", exc)

    ready = db_ok and (redis_ok or not settings.is_production)
    dependency_status = {
        "database": "healthy" if db_ok else "unavailable",
        "redis": "healthy" if redis_ok else "degraded",
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if ready else "degraded",
            "environment": settings.ENVIRONMENT,
            "dependencies": dependency_status,
        },
    )


@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def live_check():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness_check():
    return await health_check()
