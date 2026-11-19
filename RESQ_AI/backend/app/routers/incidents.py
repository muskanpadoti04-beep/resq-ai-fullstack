"""
RESQ AI - incidents router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services.audit import log_action
from app.services.auth import CurrentUser, require_role
from app.services.lifecycle import advance

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("", response_model=List[s.IncidentOut])
def get_incidents(db: Session = Depends(get_db)):
    return db.query(m.Incident).order_by(m.Incident.detected_at.desc()).all()


@router.get("/active", response_model=List[s.IncidentOut])
def get_active_incidents(db: Session = Depends(get_db)):
    return (
        db.query(m.Incident)
        .filter(m.Incident.status == "active")
        .order_by(m.Incident.risk_score.desc())
        .all()
    )


@router.get("/{incident_id}", response_model=s.IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(m.Incident).filter(m.Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def _get_incident(db: Session, incident_id: str) -> m.Incident:
    incident = db.query(m.Incident).filter(m.Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/acknowledge", response_model=s.IncidentOut)
def acknowledge_incident(incident_id: str, db: Session = Depends(get_db),
                         user: CurrentUser = Depends(require_role("operator"))):
    incident = _get_incident(db, incident_id)
    if incident.status == "resolved":
        raise HTTPException(status_code=409, detail="This incident is already resolved.")
    if incident.lifecycle == "Detected":
        advance(db, incident, "Acknowledged", actor=user.username, note="by command center operator")
        log_action(db, user, "acknowledge_incident", target=incident.incident_id)
        db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/resolve", response_model=s.IncidentOut)
def resolve_incident(incident_id: str, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(require_role("operator"))):
    """Close an incident without a rescue (fire out, false alarm). Frees any assigned team."""
    incident = _get_incident(db, incident_id)
    advance(db, incident, "Resolved", actor=user.username, note="closed by operator")
    room = db.query(m.Room).filter(m.Room.room_id == incident.room_id).first()
    if room and room.fire_status == "active":
        room.fire_status = "contained"
    if incident.assigned_team_id:
        team = db.query(m.RescueTeam).filter(m.RescueTeam.team_id == incident.assigned_team_id).first()
        if team and team.assigned_room == incident.room_id:
            team.status, team.assigned_room, team.eta_minutes, team.current_location = "Standby", None, 0, "Base"
    log_action(db, user, "resolve_incident", target=incident.incident_id)
    db.commit()
    db.refresh(incident)
    return incident
