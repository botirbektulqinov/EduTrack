"""
EduTrack — Application Entry-Point
FastAPI application factory with lifespan, CORS, and all routers mounted.

Run:   uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger("edutrack")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Startup: warm-up DB pool, verify Redis.
    Shutdown: close connections cleanly.
    """
    from app.core.database import engine
    from app.core.logging import setup_logging
    import logging as _logging

    # Initialize structured logging
    json_logs = settings.ENVIRONMENT != "development"
    setup_logging(log_level="DEBUG" if settings.ENVIRONMENT == "development" else "INFO", json_output=json_logs)
    _logger = _logging.getLogger("edutrack")

    # Verify DB connectivity (non-fatal — warn and continue)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        _logger.info("Database connection OK")
    except Exception as exc:
        _logger.warning("Database not reachable at startup: %s", exc)

    yield  # Application is running

    # Shutdown
    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="EduTrack API",
    description="Unified academic assessment platform — REST + WebSocket API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handlers (§19.1)
# ---------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTPException with standard error envelope."""
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
    """Return 422 with VALIDATION_ERROR code and field-level details."""
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
    """Catch-all: log the traceback and return a generic 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.admin.users import router as admin_users_router  # noqa: E402
from app.api.v1.admin.groups import router as admin_groups_router  # noqa: E402
from app.api.v1.admin.analytics import router as admin_analytics_router  # noqa: E402
from app.api.v1.teacher.assessments import router as teacher_assessments_router  # noqa: E402
from app.api.v1.teacher.questions import router as teacher_questions_router  # noqa: E402
from app.api.v1.teacher.results import router as teacher_results_router  # noqa: E402
from app.api.v1.teacher.analytics import router as teacher_analytics_router  # noqa: E402
from app.api.v1.student.take import router as student_take_router  # noqa: E402
from app.api.v1.student.results import router as student_results_router  # noqa: E402
from app.api.v1.student.analytics import router as student_analytics_router  # noqa: E402
from app.api.websocket.proctoring import router as ws_proctoring_router  # noqa: E402

# Auth
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])

# Admin
app.include_router(admin_users_router, prefix="/api/v1/admin/users", tags=["Admin — Users"])
app.include_router(admin_groups_router, prefix="/api/v1/admin/groups", tags=["Admin — Groups"])
app.include_router(admin_analytics_router, prefix="/api/v1/admin", tags=["Admin — Analytics"])

# Teacher
app.include_router(teacher_assessments_router, prefix="/api/v1/teacher/assessments", tags=["Teacher — Assessments"])
app.include_router(teacher_questions_router, prefix="/api/v1/teacher", tags=["Teacher — Questions"])
app.include_router(teacher_results_router, prefix="/api/v1/teacher", tags=["Teacher — Results"])
app.include_router(teacher_analytics_router, prefix="/api/v1/teacher", tags=["Teacher — Analytics"])

# Student
app.include_router(student_take_router, prefix="/api/v1/student", tags=["Student — Take Assessment"])
app.include_router(student_results_router, prefix="/api/v1/student/results", tags=["Student — Results"])
app.include_router(student_analytics_router, prefix="/api/v1/student/analytics", tags=["Student — Analytics"])

# WebSocket
app.include_router(ws_proctoring_router, tags=["WebSocket — Proctoring"])


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------
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
    return {"status": "healthy"}
