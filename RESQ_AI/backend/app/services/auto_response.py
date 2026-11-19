"""
RESQ AI - automatic response coordinator (software simulation of the field teams).

When enabled (RESQ_AUTO_RESPONSE=on) a background loop moves new incidents through the
SAME lifecycle the operator buttons use:

    Detected -> (auto) Assigned -> En Route -> On Scene -> Resolved

  1. a waiting incident (highest risk first) gets a Standby rescue team
  2. after the team's ETA the team arrives on scene
  3. after the rescue duration the team completes the rescue (occupants marked rescued,
     incident resolved, team back to Standby)

Time is compressed for demos: one "ETA minute" lasts RESQ_DEMO_SECONDS_PER_MIN real seconds.
Only incidents detected within the last RESQ_AUTO_MAX_AGE_HOURS are handled, so old seed
data is left alone. Operators can still acknowledge / dispatch / resolve by hand.

Save as backend/app/services/auto_response.py
"""
import logging
import os
import time
from datetime import datetime, timedelta

from app.database.db import SessionLocal
from app.models import models as m
from app.services.lifecycle import advance

logger = logging.getLogger("resqai")

ENABLED = os.getenv("RESQ_AUTO_RESPONSE", "off").strip().lower() in ("on", "1", "true", "yes")
CHECK_SECONDS = float(os.getenv("RESQ_AUTO_CHECK_SECONDS", "3"))
SECONDS_PER_MIN = float(os.getenv("RESQ_DEMO_SECONDS_PER_MIN", "6"))     # 5 min ETA -> 30 s
RESCUE_SECONDS = float(os.getenv("RESQ_AUTO_RESCUE_SECONDS", "25"))      # time on scene before rescue completes
MAX_AGE_HOURS = float(os.getenv("RESQ_AUTO_MAX_AGE_HOURS", "24"))
DEFAULT_ETA_MIN = 5.0
ACTOR = "RESQ AI Auto-Dispatch"


def _recent(db, **filters):
    cutoff = datetime.utcnow() - timedelta(hours=MAX_AGE_HOURS)
    q = db.query(m.Incident).filter(m.Incident.status == "active", m.Incident.detected_at >= cutoff)
    for k, v in filters.items():
        q = q.filter(getattr(m.Incident, k) == v)
    return q


def _assign_waiting(db):
    waiting = (_recent(db, assigned_team_id=None)
               .order_by(m.Incident.risk_score.desc(), m.Incident.detected_at.asc()).all())
    for inc in waiting:
        team = db.query(m.RescueTeam).filter(m.RescueTeam.status == "Standby").first()
        if team is None:
            break                                   # no free team: incident keeps waiting
        inc.assigned_team_id = team.team_id
        team.status = "En Route"
        team.assigned_room = inc.room_id
        team.current_location = "Dispatched (auto)"
        team.eta_minutes = team.eta_minutes or DEFAULT_ETA_MIN
        advance(db, inc, "Assigned", actor=ACTOR, team_name=team.team_name)
        advance(db, inc, "En Route", actor=ACTOR, team_name=team.team_name)


def _team_of(db, inc):
    return db.query(m.RescueTeam).filter(m.RescueTeam.team_id == inc.assigned_team_id).first()


def _arrivals(db):
    now = datetime.utcnow()
    for inc in _recent(db, lifecycle="En Route").all():
        team = _team_of(db, inc)
        if team is None or inc.en_route_at is None:
            continue
        travel = (DEFAULT_ETA_MIN if not team.eta_minutes else team.eta_minutes) * SECONDS_PER_MIN
        if (now - inc.en_route_at).total_seconds() >= travel:
            team.status = "On Scene"
            team.current_location = f"On scene at {team.assigned_room}"
            team.eta_minutes = 0
            advance(db, inc, "On Scene", actor=ACTOR, team_name=team.team_name)


def _complete(db):
    now = datetime.utcnow()
    for inc in _recent(db, lifecycle="On Scene").all():
        team = _team_of(db, inc)
        if team is None or inc.on_scene_at is None:
            continue
        if (now - inc.on_scene_at).total_seconds() < RESCUE_SECONDS:
            continue
        room_id = inc.room_id
        people = (db.query(m.Occupant)
                  .filter(m.Occupant.room_id == room_id, m.Occupant.is_rescued == False,  # noqa: E712
                          (m.Occupant.is_trapped == True)                                   # noqa: E712
                          | m.Occupant.risk_status.in_(["Critical", "High Risk"]))
                  .all())
        for o in people:
            o.is_rescued, o.is_trapped = True, False
        room = db.query(m.Room).filter(m.Room.room_id == room_id).first()
        if room:
            room.occupants_count = max((room.occupants_count or 0) - len(people), 0)
        humans = sum(1 for o in people if o.type == "Human")
        db.add(m.IncidentTimeline(
            incident_id=inc.incident_id, timestamp=now, actor=team.team_name,
            event=f"{team.team_name} completed rescue in {room_id}: {humans} people, {len(people) - humans} animals evacuated"))
        advance(db, inc, "Resolved", actor=ACTOR, team_name=team.team_name)
        if room and room.fire_status == "active":
            room.fire_status = "contained"
        team.status, team.assigned_room, team.eta_minutes, team.current_location = "Standby", None, 0, "Base"


def run_auto_response(db):
    """One pass. Safe to call repeatedly; each step only touches incidents in its own state."""
    _assign_waiting(db)
    _arrivals(db)
    _complete(db)
    db.commit()


def _loop():
    while True:
        time.sleep(CHECK_SECONDS)
        db = SessionLocal()
        try:
            run_auto_response(db)
        except Exception:                      # never let the thread die (e.g. SQLite "database is locked")
            db.rollback()
            logger.exception("Auto-response pass failed")
        finally:
            db.close()


def start_auto_response():
    if not ENABLED:
        return False
    import threading
    threading.Thread(target=_loop, daemon=True, name="auto-response").start()
    logger.info("Auto-response ON (%.0fs per ETA minute, %.0fs on scene)", SECONDS_PER_MIN, RESCUE_SECONDS)
    return True
