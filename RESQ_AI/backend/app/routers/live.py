"""Live-update helper + notifications."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models import models as m
from app.services import live
from app.services.auth import CurrentUser, require_role
from app.services.notifications import run_escalation

router = APIRouter(tags=["Live"])


@router.get("/api/live/version")
def live_version():
    """Changes whenever anything in the database is committed. Poll this every few seconds and
    reload data only when the number changes."""
    return {"version": live.current(), "server_time": datetime.utcnow().isoformat()}


def _out(n):
    return {"id": n.id, "time": n.created_at.isoformat(), "level": n.level, "kind": n.kind,
            "incident_id": n.incident_id, "room_id": n.room_id, "message": n.message,
            "escalation_level": n.escalation_level, "channel": n.channel, "read": n.read}


@router.get("/api/notifications")
def notifications(limit: int = 30, db: Session = Depends(get_db)):
    run_escalation(db)       # make sure anything due is created even if the background check has not run yet
    rows = db.query(m.Notification).order_by(m.Notification.id.desc()).limit(min(limit, 200)).all()
    return {"unread": db.query(m.Notification).filter(m.Notification.read == False).count(),  # noqa: E712
            "items": [_out(n) for n in rows]}


@router.post("/api/notifications/read")
def mark_read(db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("operator"))):
    n = db.query(m.Notification).filter(m.Notification.read == False).update({"read": True})  # noqa: E712
    db.commit()
    return {"marked_read": n}
