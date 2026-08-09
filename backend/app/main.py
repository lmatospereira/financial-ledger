"""FastAPI application entrypoint.

Mounts the API routers under /api. A commented-out block near the bottom
shows where to later mount the built frontend (frontend/dist) as static
files for a single-container deployment.
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import auth, crud
from app.database import SessionLocal

logger = logging.getLogger("app.errors")
from app.db_migrations import run_migrations
from app.limiter import limiter
from app.routers import accounts as accounts_router
from app.routers import alerts as alerts_router
from app.routers import auth as auth_router
from app.routers import bills as bills_router
from app.routers import budgets as budgets_router
from app.routers import categories as categories_router
from app.routers import goals as goals_router
from app.routers import investments as investments_router
from app.routers import recurring_transactions as recurring_transactions_router
from app.routers import reports as reports_router
from app.routers import transactions as transactions_router
from app.routers import transfers as transfers_router
from app.routers import users as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    _seed_admin_user()
    yield


app = FastAPI(title="Livro Caixa API", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS: allow the frontend dev server (and any origins configured via env)
# to call the API. Tighten/override CORS_ORIGINS in production.
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(accounts_router.router)
app.include_router(categories_router.router)
app.include_router(budgets_router.router)
app.include_router(transactions_router.router)
app.include_router(recurring_transactions_router.router)
app.include_router(transfers_router.router)
app.include_router(bills_router.router)
app.include_router(goals_router.router)
app.include_router(alerts_router.router)
app.include_router(reports_router.router)
app.include_router(investments_router.router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten FastAPI's default `[{loc, msg, type, ...}, ...]` validation
    error shape into `{"detail": "<string>"}` so every error response from
    this API has the same shape as our manual HTTPExceptions.
    """
    messages = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        msg = error.get("msg", "Invalid input")
        messages.append(f"{loc}: {msg}" if loc else msg)
    detail = "; ".join(messages) if messages else "Invalid request"
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with a consistent error shape."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Explicitly log the full traceback for any unhandled exception.

    Added because a real production 500 on the investments screen produced
    no visible traceback in `docker logs` despite PYTHONUNBUFFERED=1 -- this
    guarantees the next occurrence is captured regardless of whatever was
    suppressing Starlette/uvicorn's default error logging.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def _seed_admin_user() -> None:
    """Create the single admin user from env vars if the User table is empty."""
    db = SessionLocal()
    try:
        if crud.count_users(db) == 0:
            username = os.getenv("ADMIN_USERNAME")
            password = os.getenv("ADMIN_PASSWORD")
            if username and password:
                username = username.strip().lower()
                crud.create_user(
                    db,
                    username=username,
                    # No ADMIN_NAME env var to keep deploy config minimal --
                    # admins can rename themselves via PUT /api/users/{id}.
                    name=os.getenv("ADMIN_NAME", username.capitalize()),
                    password_hash=auth.hash_password(password),
                    is_admin=True,
                )
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve the built frontend for single-container deployment (no Nginx/domain/
# HTTPS yet). Registered last so it never shadows /api routes, which are
# matched first. Path is relative to backend/'s working directory (the
# Docker image and local dev both keep frontend/ as a sibling of backend/),
# and is skipped if the frontend hasn't been built yet so plain
# `uvicorn app.main:app` still works during backend-only development.
#
# This is a manual catch-all instead of `StaticFiles(html=True)` mounted at
# "/": that only auto-serves index.html for the root and real directories,
# so a direct/refreshed request for a client-side route like /login or
# /accounts (no matching file on disk) 404s instead of handing off to the
# React app. Here, hashed build assets are served normally via StaticFiles,
# and everything else falls back to index.html so react-router can take over.
# ---------------------------------------------------------------------------
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
