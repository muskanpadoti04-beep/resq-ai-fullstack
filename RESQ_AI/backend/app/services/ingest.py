"""ONE pipeline for sensor data. The simulator, CSV import, the batch API and (later) a real
sensor gateway all call ingest_reading(), so every source gets the same validation, the same
risk calculation and the same incident/notification behaviour.

Changes in this version (marked CHANGED):
  1. A single spike without a flame no longer opens an incident: the room must stay above the
     threshold for CONFIRM_READINGS readings in a row (a flame with a Critical score is instant).
  2. A room whose fire_status is 'active' or 'contained' goes back to 'none' once its readings are
     normal and no incident is open for it. Before, it stayed on fire forever after the first flame.
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import models as m
from app.services.risk_engine import calculate_risk, severity_from_risk_level
from app.services.validation import validate_sensor_reading
from app.services.notifications import notify

AUTO_INCIDENT_THRESHOLD = 60   # score above this (High Risk / Critical) opens an incident automatically
CONFIRM_READINGS = int(os.getenv("RESQ_CONFIRM_READINGS", "2"))   # CHANGED: consecutive high readings needed
CLEAR_TEMP, CLEAR_SMOKE = 45.0, 35.0                              # CHANGED: "readings are normal" limits

_streak = {}   # CHANGED: room_id -> number of consecutive readings above the threshold (in memory)


class IngestError(ValueError):
    pass


def ingest_reading(db: Session, room: m.Room, *, temperature: Optional[float], smoke_level: Optional[float],
                   co_level: Optional[float], humidity: Optional[float] = None, flame_detected: bool = False,
                   source: str = "api", when: Optional[datetime] = None) -> dict:
    """Validate, store, score. Does NOT commit (caller commits). Raises IngestError on invalid data."""
    problems = validate_sensor_reading(temperature, smoke_level, co_level, humidity)
    if problems:
        raise IngestError("; ".join(problems))
    now = when or datetime.utcnow()

    room.temperature = temperature
    room.smoke_level = smoke_level
    room.last_sensor_update = now
    if flame_detected:
        room.fire_status = "active"          # a flame sensor trip is treated as an active fire
    elif (room.fire_status in ("active", "contained")            # CHANGED: let a room recover
          and temperature is not None and smoke_level is not None
          and temperature < CLEAR_TEMP and smoke_level < CLEAR_SMOKE):
        still_open = (db.query(m.Incident)
                      .filter(m.Incident.room_id == room.room_id, m.Incident.status == "active").first())
        if not still_open:
            room.fire_status = "none"
    result = calculate_risk(temperature=temperature, smoke_level=smoke_level, co_level=co_level,
                            flame_detected=flame_detected, fire_status=room.fire_status,
                            occupants_count=room.occupants_count or 0)
    room.risk_level = result["risk_level"]
    db.add(m.SensorReading(
        reading_id=f"RD-{source[:6].upper()}-{int(now.timestamp())}-{uuid.uuid4().hex[:6]}",
        room_id=room.room_id, timestamp=now, temperature=temperature, smoke_level=smoke_level,
        co_level=co_level, flame_detected=flame_detected, humidity=humidity))

    above = result["risk_score"] > AUTO_INCIDENT_THRESHOLD
    _streak[room.room_id] = _streak.get(room.room_id, 0) + 1 if above else 0       # CHANGED
    confirmed = above and (_streak[room.room_id] >= CONFIRM_READINGS
                           or (flame_detected and result["risk_score"] >= 81))     # CHANGED