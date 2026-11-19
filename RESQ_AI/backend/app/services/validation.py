"""
RESQ AI - data validation for buildings, rooms, occupants, incidents and sensor readings.

Each validate_* function returns a list of problems (empty list = valid). The seed script
skips invalid rows and reports them; the API uses the same limits for incoming sensor data.
"""
from typing import Optional

TEMP_RANGE = (-40.0, 1200.0)      # degrees C
SMOKE_RANGE = (0.0, 100.0)        # percent obscuration
CO_RANGE = (0.0, 1000.0)          # ppm
HUMIDITY_RANGE = (0.0, 100.0)

OCCUPANT_TYPES = {"Human", "Dog", "Cat", "Pet"}
AGE_GROUPS = {"Child", "Adult", "Senior", "N/A"}
RISK_LEVELS = {"Safe", "Moderate", "High Risk", "Critical"}
SEVERITIES = {"Low", "Moderate", "High", "Critical"}
FIRE_STATUSES = {"none", "smoke", "active", "contained"}
INCIDENT_TYPES = {"Fire", "Smoke Detection", "Gas Leak", "Electrical Fault"}


def _num(value, name, lo, hi, problems, required=True):
    if value is None or value == "":
        if required:
            problems.append(f"{name} is missing")
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        problems.append(f"{name} is not a number: {value!r}")
        return None
    if not (lo <= v <= hi):
        problems.append(f"{name} {v} is outside the valid range {lo} to {hi}")
    return v


def validate_room(row: dict) -> list:
    p = []
    if not row.get("room_id"):
        p.append("room_id is missing")
    _num(row.get("floor"), "floor", 1, 200, p)
    cap = _num(row.get("capacity"), "capacity", 0, 10000, p)
    occ = _num(row.get("occupants"), "occupants", 0, 10000, p)
    if cap is not None and occ is not None and occ > cap:
        p.append(f"occupants ({int(occ)}) exceed capacity ({int(cap)})")
    _num(row.get("temperature"), "temperature", *TEMP_RANGE, p, required=False)
    _num(row.get("smoke_level"), "smoke_level", *SMOKE_RANGE, p, required=False)
    if row.get("fire_status") not in FIRE_STATUSES:
        p.append(f"fire_status {row.get('fire_status')!r} is not one of {sorted(FIRE_STATUSES)}")
    if row.get("risk_level") not in RISK_LEVELS:
        p.append(f"risk_level {row.get('risk_level')!r} is not valid")
    return p


def validate_occupant(row: dict, known_rooms: set) -> list:
    p = []
    if not row.get("occupant_id"):
        p.append("occupant_id is missing")
    if row.get("room_id") not in known_rooms:
        p.append(f"room {row.get('room_id')!r} does not exist")
    if row.get("type") not in OCCUPANT_TYPES:
        p.append(f"type {row.get('type')!r} is not one of {sorted(OCCUPANT_TYPES)}")
    if row.get("age_group") not in AGE_GROUPS:
        p.append(f"age_group {row.get('age_group')!r} is not one of {sorted(AGE_GROUPS)}")
    if row.get("risk_status") not in RISK_LEVELS:
        p.append(f"risk_status {row.get('risk_status')!r} is not valid")
    return p


def validate_incident(row: dict, known_rooms: set) -> list:
    p = []
    if not row.get("incident_id"):
        p.append("incident_id is missing")
    if row.get("room") not in known_rooms:
        p.append(f"room {row.get('room')!r} does not exist")
    if row.get("incident_type") not in INCIDENT_TYPES:
        p.append(f"incident_type {row.get('incident_type')!r} is not valid")
    _num(row.get("temperature"), "temperature", *TEMP_RANGE, p)
    _num(row.get("smoke_level"), "smoke_level", *SMOKE_RANGE, p)
    _num(row.get("occupants_count"), "occupants_count", 0, 10000, p)
    if row.get("fire_status") not in FIRE_STATUSES:
        p.append(f"fire_status {row.get('fire_status')!r} is not valid")
    return p


def validate_sensor_reading(temperature: Optional[float], smoke_level: Optional[float],
                            co_level: Optional[float], humidity: Optional[float] = None) -> list:
    p = []
    _num(temperature, "temperature", *TEMP_RANGE, p, required=False)
    _num(smoke_level, "smoke_level", *SMOKE_RANGE, p, required=False)
    _num(co_level, "co_level", *CO_RANGE, p, required=False)
    _num(humidity, "humidity", *HUMIDITY_RANGE, p, required=False)
    return p
