"""
RESQ AI - incident lifecycle.

    Detected -> Acknowledged -> Assigned -> En Route -> On Scene -> Resolved

A state can only move forward. If an action skips states (for example dispatching a
team to an incident nobody acknowledged yet) the skipped states are recorded as
automatic steps, so every incident has a complete, timestamped history.
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import LIFECYCLE
from app.models import models as m

_TIME_FIELD = {
    "Acknowledged": "acknowledged_at",
    "Assigned": "dispatched_at",      # first assignment time; also drives Avg Response Time
    "En Route": "en_route_at",
    "On Scene": "on_scene_at",
    "Resolved": "resolved_at",
}
_EVENT_TEXT = {
    "Acknowledged": "Incident acknowledged",
    "Assigned": "Rescue team assigned",
    "En Route": "Rescue team en route",
    "On Scene": "Rescue team arrived on scene",
    "Resolved": "Incident resolved",
}


def index_of(state: str) -> int:
    return LIFECYCLE.index(state) if state in LIFECYCLE else 0


def advance(db: Session, incident: m.Incident, target: str, actor: str,
            team_name: Optional[str] = None, note: Optional[str] = None) -> None:
    """Moves `incident` forward to `target`, recording each step. Never moves backwards."""
    if target not in LIFECYCLE:
        raise HTTPException(status_code=400, detail=f"Unknown incident state: {target}")
    current = index_of(incident.lifecycle or "Detected")
    if incident.status == "resolved" or current >= LIFECYCLE.index("Resolved"):
        raise HTTPException(status_code=409, detail="This incident is already resolved.")
    goal = LIFECYCLE.index(target)
    if goal <= current:
        return  # already at (or past) this state - nothing to do
    now = datetime.utcnow()
    for i in range(current + 1, goal + 1):
        state = LIFECYCLE[i]
        field = _TIME_FIELD[state]
        if getattr(incident, field) is None:
            setattr(incident, field, now)
        incident.lifecycle = state
        auto = i < goal
        text = _EVENT_TEXT[state] + (f" - {team_name}" if team_name and state in ("Assigned", "En Route", "On Scene") else "")
        if auto:
            text += " (automatic)"
        elif note:
            text += f" - {note}"
        db.add(m.IncidentTimeline(incident_id=incident.incident_id, timestamp=now, event=text, actor=actor))
    if target == "Acknowledged" or goal >= LIFECYCLE.index("Acknowledged"):
        incident.acknowledged = True
    if target == "Resolved":
        incident.status = "resolved"
