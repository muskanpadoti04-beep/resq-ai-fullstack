"""Notifications + escalation rules.

Rule: an ACTIVE incident that is still 'Detected' (nobody acknowledged it) after ESCALATE_MINUTES is
escalated; the alert repeats at 2x, 3x ... that time with a higher escalation level (max 3).
Level 1 -> duty operator reminder, 2 -> supervisor, 3 -> incident commander / emergency services.
Only dashboard notifications exist today; other channels (SMS/e-mail) would plug in at notify().
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app import config
from app.models import models as m

ESCALATION_TARGETS = {1: "duty operator", 2: "supervisor", 3: "incident commander / emergency services"}


def notify(db: Session, level: str, kind: str, message: str, incident_id: Optional[str] = None,
           room_id: Optional[str] = None, escalation_level: int = 0) -> m.Notification:
    n = m.Notification(level=level, kind=kind, message=message, incident_id=incident_id,
                       room_id=room_id, escalation_level=escalation_level)
    db.add(n)
    return n


def run_escalation(db: Session, now: Optional[datetime] = None) -> int:
    """Create escalation notifications that are due. Safe to call repeatedly (idempotent per level)."""
    now = now or datetime.utcnow()
    created = 0
    oldest = now - timedelta(hours=config.ESCALATE_MAX_AGE_HOURS)
    incidents = (db.query(m.Incident)
                 .filter(m.Incident.status == "active", m.Incident.lifecycle == "Detected",
                         m.Incident.detected_at >= oldest).all())
    for inc in incidents:
        waited = (now - inc.detected_at).total_seconds() / 60
        due_level = min(int(waited // config.ESCALATE_MINUTES), 3)
        if due_level < 1:
            continue
        done = {n.escalation_level for n in db.query(m.Notification).filter(
            m.Notification.incident_id == inc.incident_id, m.Notification.kind == "escalation").all()}
        for lvl in range(1, due_level + 1):
            if lvl in done:
                continue
            notify(db, "critical", "escalation",
                   f"Incident {inc.incident_id} ({inc.room_id}, {inc.risk_level}) unacknowledged for "
                   f"{int(waited)} min - escalated to {ESCALATION_TARGETS[lvl]}",
                   incident_id=inc.incident_id, room_id=inc.room_id, escalation_level=lvl)
            created += 1
    if created:
        db.commit()
    return created
