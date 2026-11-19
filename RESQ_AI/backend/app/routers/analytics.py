"""
RESQ AI - analytics endpoints
Save as backend/app/routers/analytics.py  (needs backend/app/services/analytics_calc.py)
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.db import get_db
from app.models import models as m
from app.services.analytics_calc import build_summary, downsample, iso_z, pick_default_room

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ---------------- new: one call for the whole analytics page ----------------
@router.get("/summary")
def analytics_summary(db: Session = Depends(get_db)):
    return build_summary(
        db.query(m.Incident).all(),
        db.query(m.Occupant).all(),
        db.query(m.Room).all(),
        db.query(m.Floor).all(),
        datetime.utcnow(),
    )


@router.get("/sensor-history")
def sensor_history(
    room_id: Optional[str] = None,
    minutes: int = Query(30, ge=1, le=1440),
    max_points: int = Query(120, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """Recent readings of ONE room (default: the room with the worst active incident), thinned for the chart."""
    rooms = db.query(m.Room).order_by(m.Room.room_id).all()
    if not room_id:
        incidents = db.query(m.Incident).filter(m.Incident.status == "active").all()
        room_id = pick_default_room(rooms, incidents)
    since = datetime.utcnow() - timedelta(minutes=minutes)
    rows = (
        db.query(m.SensorReading)
        .filter(m.SensorReading.room_id == room_id, m.SensorReading.timestamp >= since)
        .order_by(m.SensorReading.timestamp.asc())
        .all()
    )
    points = [
        {"t": iso_z(r.timestamp), "temperature": r.temperature, "smoke_level": r.smoke_level, "co_level": r.co_level}
        for r in rows
    ]
    return {"room_id": room_id, "rooms": [r.room_id for r in rooms], "minutes": minutes, "points": downsample(points, max_points)}


# ---------------- existing endpoints (kept so other pages keep working) ----------------
@router.get("/occupants")
def analytics_occupants(db: Session = Depends(get_db)):
    rows = (
        db.query(m.Occupant.risk_status, func.count(m.Occupant.id))
        .group_by(m.Occupant.risk_status)
        .all()
    )
    return [{"risk_status": r[0], "count": r[1]} for r in rows]


@router.get("/incidents")
def analytics_incidents(db: Session = Depends(get_db)):
    by_floor = (
        db.query(m.Incident.floor, func.count(m.Incident.id))
        .group_by(m.Incident.floor)
        .all()
    )
    by_severity = (
        db.query(m.Incident.severity, func.count(m.Incident.id))
        .group_by(m.Incident.severity)
        .all()
    )
    return {
        "by_floor": [{"floor": r[0], "count": r[1]} for r in by_floor],
        "by_severity": [{"severity": r[0], "count": r[1]} for r in by_severity],
    }


@router.get("/risk")
def analytics_risk(db: Session = Depends(get_db)):
    # Only the newest 3000 readings: with the sensor simulator running, "all readings" grows without limit.
    readings = (
        db.query(m.SensorReading)
        .order_by(m.SensorReading.timestamp.desc())
        .limit(3000)
        .all()
    )
    readings.reverse()
    temperature_series = [
        {"timestamp": iso_z(r.timestamp), "temperature": r.temperature, "room_id": r.room_id}
        for r in readings
    ]
    smoke_series = [
        {"timestamp": iso_z(r.timestamp), "smoke_level": r.smoke_level, "room_id": r.room_id}
        for r in readings
    ]

    teams = db.query(m.RescueTeam).all()
    response_times = [
        {"team_name": t.team_name, "eta_minutes": t.eta_minutes}
        for t in teams if t.eta_minutes
    ]

    return {
        "temperature_over_time": temperature_series,
        "smoke_over_time": smoke_series,
        "response_times": response_times,
    }