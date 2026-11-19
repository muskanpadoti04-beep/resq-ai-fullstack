"""
RESQ AI - Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination
FastAPI application entrypoint
"""
import os
import logging
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # must run before the app modules read RESQ_* settings

from app.services.auth import require_role, seed_default_users  # noqa: E402
from app.database.db import Base, engine  # noqa: E402
from app.routers import core, incidents, response, analytics, simulation, auth as auth_router, topology as topology_router, ml as ml_router, sensors as sensors_router, live as live_router  # noqa: E402

# Ensure tables exist even if seed_database.py hasn't been run yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RESQ AI API",
    description=(
        "RESQ AI — Intelligent Fire Detection, Risk Prediction & Rescue Response "
        "Coordination. Backend REST API powering the fire safety command center "
        "dashboard prototype."
    ),
    version="1.0.0",
)

logger = logging.getLogger("resqai")


@app.middleware("http")
async def catch_unhandled_errors(request: Request, call_next):
    """Registered before CORS, so even 500 responses carry CORS headers and the
    browser shows the real error instead of a misleading 'network error'."""
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Unexpected server error.", "code": "server_error"})


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # any local dev port (e.g. Vite falling back to 5174) is allowed too
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- consistent JSON errors: {"detail": "<human readable>", "code": "<machine code>"} ----
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Integrity error on %s: %s", request.url.path, exc.orig)
    return JSONResponse(status_code=409, content={
        "detail": "Conflict: the data refers to something that does not exist or already exists.",
        "code": "db_integrity"})


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    logger.error("Database unavailable on %s: %s", request.url.path, exc.orig)
    return JSONResponse(status_code=503, content={
        "detail": "Database is unavailable or out of date. Re-run seed_database.py and restart the backend.",
        "code": "db_unavailable"})


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Database error.", "code": "db_error"})


# Login endpoints are open; everything else needs at least a signed-in viewer.
# (Actions that change data additionally require the operator or admin role - see each router.)
_signed_in = [Depends(require_role("viewer"))]
app.include_router(auth_router.router)
app.include_router(core.router, dependencies=_signed_in)
app.include_router(incidents.router, dependencies=_signed_in)
app.include_router(response.router, dependencies=_signed_in)
app.include_router(analytics.router, dependencies=_signed_in)
app.include_router(simulation.router, dependencies=_signed_in)
app.include_router(topology_router.router, dependencies=_signed_in)
app.include_router(ml_router.router, dependencies=_signed_in)
app.include_router(live_router.router, dependencies=_signed_in)
# Sensor adapter: authenticates itself (operator login OR X-Device-Key), so it is not behind _signed_in
app.include_router(sensors_router.router)
app.include_router(sensors_router.camera_router)


@app.on_event("startup")
def bootstrap_defaults():
    """Make sure demo accounts and the building map exist, even on a database seeded earlier."""
    from app.database.db import SessionLocal
    from app.services.topology import build_topology
    db = SessionLocal()
    try:
        seed_default_users(db)
        build_topology(db)
    except SQLAlchemyError as exc:
        logger.warning("Startup setup skipped (database out of date? re-run seed_database.py): %s", exc)
    finally:
        db.close()


def _escalation_loop():
    """Background check: raises escalation notifications even if nobody has the dashboard open."""
    import time
    from app import config
    from app.database.db import SessionLocal
    from app.services.notifications import run_escalation
    while True:
        time.sleep(config.ESCALATION_CHECK_SECONDS)
        db = SessionLocal()
        try:
            run_escalation(db)
        except Exception:            # never let the checker thread die
            logger.exception("Escalation check failed")
        finally:
            db.close()


@app.on_event("startup")
def start_escalation_checker():
    import threading
    threading.Thread(target=_escalation_loop, daemon=True, name="escalation-checker").start()


@app.on_event("startup")
def start_auto_response_loop():
    from app.services.auto_response import start_auto_response
    start_auto_response()


@app.get("/")

@app.get("/")
def root():
    return {
        "project": "RESQ AI",
        "tagline": "Detect. Locate. Rescue. Save Lives.",
        "docs": "/docs",
        "status": "online",
    }


@app.get("/api/health")
def health():
    """Liveness + database check (used by the frontend to explain connection problems)."""
    from sqlalchemy import text
    from app.database.db import SessionLocal
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})
    finally:
        db.close()
