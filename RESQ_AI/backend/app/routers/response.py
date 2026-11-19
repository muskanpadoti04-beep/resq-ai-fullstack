"""
RESQ AI - rescue teams, medical support, timeline
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services.audit import log_action
from app.services.auth import CurrentUser, require_role
from app.services.lifecycle import advance

router = APIRouter(tags=["Response"])


@router.get("/api/rescue-teams", response_model=List[s.RescueTeamOut])
def get_rescue_teams(db: Session = Depends(get_db)):
    return db.query(m.RescueTeam).all()


def _get_team(db: Session, team_id: str) -> m.RescueTeam:
    team = db.query(m.RescueTeam).filter(m.RescueTeam.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Rescue team not found")
    return team


def _incident_of(db: Session, team: m.RescueTeam):
    """The active incident this team is working on (by assignment, else by room)."""
    inc = (
        db.query(m.Incident)
        .filter(m.Incident.assigned_team_id == team.team_id, m.Incident.status == "active")
        .first()
    )
    if not inc and team.assigned_room:
        inc = (
            db.query(m.Incident)
            .filter(m.Incident.room_id == team.assigned_room, m.Incident.status == "active")
            .first()
        )
    return inc


@router.post("/api/rescue-teams/{team_id}/dispatch", response_model=s.RescueTeamOut)
def dispatch_team(
    team_id: str,
    incident_id: Optional[str] = Query(None, description="Incident to send the team to (default: highest-risk incident without a team)"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("operator")),
):
    team = _get_team(db, team_id)
    if team.status != "Standby":
        raise HTTPException(status_code=409, detail=f"{team.team_name} is already deployed ({team.status}).")

    if incident_id:
        incident = db.query(m.Incident).filter(m.Incident.incident_id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        if incident.status != "active":
            raise HTTPException(status_code=409, detail="That incident is already resolved.")
        if incident.assigned_team_id:
            raise HTTPException(status_code=409, detail="A rescue team is already assigned to that incident.")
    else:
        incident = (
            db.query(m.Incident)
            .filter(m.Incident.status == "active", m.Incident.assigned_team_id.is_(None))
            .order_by(m.Incident.risk_score.desc(), m.Incident.detected_at.asc())
            .first()
        )
        if not incident:
            raise HTTPException(status_code=409, detail="No incident is waiting for a rescue team.")

    incident.assigned_team_id = team.team_id
    team.status = "En Route"
    team.assigned_room = incident.room_id
    team.current_location = "Dispatched"
    if not team.eta_minutes:
        team.eta_minutes = 5
    advance(db, incident, "Assigned", actor=user.username, team_name=team.team_name)
    advance(db, incident, "En Route", actor=user.username, team_name=team.team_name)
    log_action(db, user, "dispatch_team", target=team.team_id, detail=f"{team.team_name} -> {incident.room_id} ({incident.incident_id})")
    db.commit()
    db.refresh(team)
    return team


@router.post("/api/rescue-teams/{team_id}/arrive", response_model=s.RescueTeamOut)
def team_arrived(team_id: str, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(require_role("operator"))):
    """Team reports it has reached the room (En Route -> On Scene)."""
    team = _get_team(db, team_id)
    if team.status != "En Route":
        raise HTTPException(status_code=409, detail=f"{team.team_name} is not en route (status: {team.status}).")
    incident = _incident_of(db, team)
    team.status = "On Scene"
    team.current_location = f"On scene at {team.assigned_room}"
    team.eta_minutes = 0
    if incident:
        advance(db, incident, "On Scene", actor=user.username, team_name=team.team_name)
    log_action(db, user, "team_arrived", target=team.team_id, detail=f"{team.team_name} on scene at {team.assigned_room}")
    db.commit()
    db.refresh(team)
    return team


@router.post("/api/rescue-teams/{team_id}/complete-rescue")
def complete_rescue(team_id: str, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(require_role("operator"))):
    """
    Rescue team finished at its assigned room: everyone who was trapped or at
    high/critical risk there is marked rescued ('People Rescued' counts these)
    and the incident is resolved.
    """
    team = _get_team(db, team_id)
    if not team.assigned_room or team.status == "Standby":
        raise HTTPException(status_code=400, detail="Team is not deployed to a room")

    room_id = team.assigned_room
    incident = _incident_of(db, team)
    if incident:
        advance(db, incident, "On Scene", actor=user.username, team_name=team.team_name)

    people = (
        db.query(m.Occupant)
        .filter(
            m.Occupant.room_id == room_id,
            m.Occupant.is_rescued == False,  # noqa: E712
            (m.Occupant.is_trapped == True)  # noqa: E712
            | m.Occupant.risk_status.in_(["Critical", "High Risk"]),
        )
        .all()
    )
    for o in people:
        o.is_rescued = True
        o.is_trapped = False
    room = db.query(m.Room).filter(m.Room.room_id == room_id).first()
    if room:
        room.occupants_count = max((room.occupants_count or 0) - len(people), 0)
    humans = sum(1 for o in people if o.type == "Human")
    animals = len(people) - humans

    db.add(m.IncidentTimeline(
        incident_id=incident.incident_id if incident else None,
        timestamp=datetime.utcnow(),
        event=f"{team.team_name} completed rescue in {room_id}: {humans} people, {animals} animals evacuated",
        actor=team.team_name,
    ))
    if incident:
        advance(db, incident, "Resolved", actor=user.username, team_name=team.team_name)
        if room and room.fire_status == "active":
            room.fire_status = "contained"
    team.status = "Standby"
    team.assigned_room = None
    team.eta_minutes = 0
    team.current_location = "Base"
    log_action(db, user, "complete_rescue", target=team.team_id,
               detail=f"{room_id}: {humans} people, {animals} animals rescued")
    db.commit()
    return {"team_id": team.team_id, "room_id": room_id, "people_rescued": humans, "animals_rescued": animals}


@router.post("/api/rescue-teams/{team_id}/navigate", response_model=s.RescueTeamOut)
def navigate_team(team_id: str, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_role("operator"))):
    team = _get_team(db, team_id)
    if not team.assigned_room:
        raise HTTPException(status_code=409, detail=f"{team.team_name} has no assigned room. Dispatch it first.")
    incident = _incident_of(db, team)
    if team.status == "Standby":
        team.status = "En Route"
    team.current_location = "Navigating to assigned room"
    if incident:
        advance(db, incident, "En Route", actor=user.username, team_name=team.team_name)
    db.add(m.IncidentTimeline(
        incident_id=incident.incident_id if incident else None,
        timestamp=datetime.utcnow(),
        event=f"Navigation started for {team.team_name} to {team.assigned_room}",
        actor=user.username,
    ))
    log_action(db, user, "navigate_team", target=team.team_id, detail=f"to {team.assigned_room}")
    db.commit()
    db.refresh(team)
    return team


@router.get("/api/medical-support", response_model=List[s.MedicalSupportOut])
def get_medical_support(db: Session = Depends(get_db)):
    return db.query(m.MedicalSupport).all()


@router.get("/api/timeline", response_model=List[s.TimelineOut])
def get_timeline(db: Session = Depends(get_db)):
    return db.query(m.IncidentTimeline).order_by(m.IncidentTimeline.timestamp.desc()).limit(100).all()