"""
RESQ AI - risk calculation endpoint + demo fire simulation endpoint
"""
import os
import sys
import uuid
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db, Base
from app.models import models as m
from app.schemas import schemas as s
from app.services.audit import log_action
from app.services.auth import CurrentUser, require_role
from app.services.risk_engine import calculate_risk, severity_from_risk_level

router = APIRouter(tags=["Risk & Simulation"])


@router.post("/api/risk/calculate", response_model=s.RiskCalculateResponse)
def risk_calculate(payload: s.RiskCalculateRequest):
    result = calculate_risk(
        temperature=payload.temperature,
        smoke_level=payload.smoke_level,
        co_level=payload.co_level,
        flame_detected=payload.flame_detected,
        fire_status=payload.fire_status,
        occupants_count=payload.occupants_count,
        exit_blocked=payload.exit_blocked,
    )
    return s.RiskCalculateResponse(**result)


@router.post("/api/simulation/fire")
def simulate_fire(db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_role("operator"))):
    """
    Demo-only endpoint: picks a random room, escalates its sensor readings,
    recalculates risk with the risk engine, creates/updates an incident and
    timeline entry, and returns the resulting incident. Lets a teacher watch
    the dashboard update live.
    """
    rooms = db.query(m.Room).all()
    if not rooms:
        raise HTTPException(status_code=404, detail="No rooms available to simulate")

    # Prefer a room that actually has people in it, so the rescue flow is visible
    occupied_ids = {o.room_id for o in db.query(m.Occupant).filter(m.Occupant.is_rescued == False).all()}  # noqa: E712
    candidates = [r for r in rooms if r.room_id in occupied_ids and r.fire_status != "active"] or rooms
    room = random.choice(candidates)

    # Escalate sensor state
    room.temperature = round(random.uniform(90, 145), 1)
    room.smoke_level = round(random.uniform(75, 100), 1)
    room.fire_status = "active"
    room.last_sensor_update = datetime.utcnow()
    co_level = round(random.uniform(90, 180), 1)
    room_people = db.query(m.Occupant).filter(
        m.Occupant.room_id == room.room_id, m.Occupant.is_rescued == False  # noqa: E712
    ).all()
    occupants_count = len(room_people) or room.occupants_count or random.randint(1, 4)
    exit_blocked = random.random() < 0.4

    result = calculate_risk(
        temperature=room.temperature,
        smoke_level=room.smoke_level,
        co_level=co_level,
        flame_detected=True,
        fire_status="active",
        occupants_count=occupants_count,
        exit_blocked=exit_blocked,
    )
    room.risk_level = result["risk_level"]

    # People in the burning room are now at risk; some may be trapped
    for o in room_people:
        o.risk_status = "Critical" if result["risk_level"] == "Critical" else "High Risk"
        o.is_trapped = random.random() < (0.7 if exit_blocked else 0.3)
    db.add(m.SensorReading(
        reading_id=f"RD-SIM-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:6]}",
        room_id=room.room_id,
        timestamp=datetime.utcnow(),
        temperature=room.temperature,
        smoke_level=room.smoke_level,
        co_level=co_level,
        flame_detected=True,
        humidity=round(random.uniform(20, 40), 1),
    ))

    incident_id = f"INC-SIM-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:6]}"
    incident = m.Incident(
        incident_id=incident_id,
        building_id="BLD-01",
        floor=room.floor_number,
        room_id=room.room_id,
        incident_type="Fire",
        severity=severity_from_risk_level(result["risk_level"]),
        temperature=room.temperature,
        smoke_level=room.smoke_level,
        fire_status="active",
        detected_at=datetime.utcnow(),
        occupants_count=occupants_count,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        acknowledged=False,
        status="active",
        lifecycle="Detected",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    blocked_stair = None
    if exit_blocked:
        # a blocked escape route: one stairwell on the fire floor is cut off (shows up in routing)
        stair = db.query(m.TopologyNode).filter(
            m.TopologyNode.node_id == f"S:{random.choice('AB')}:{room.floor_number}").first()
        if stair and not stair.blocked:
            stair.blocked = True
            stair.blocked_reason = f"Blocked by fire debris near {room.room_id} (simulated)"
            blocked_stair = stair.label
            db.add(m.IncidentTimeline(
                incident_id=incident.incident_id, timestamp=datetime.utcnow(),
                event=f"{stair.label} blocked - evacuation routes recalculated",
                actor="RESQ AI Simulation Engine"))
    log_action(db, user, "simulate_fire", target=incident.incident_id,
               detail=f"{room.room_id}, risk {result['risk_score']} ({result['risk_level']})"
                      + (f", {blocked_stair} blocked" if blocked_stair else ""))

    db.add(m.IncidentTimeline(
        incident_id=incident.incident_id,
        timestamp=datetime.utcnow(),
        event=f"SIMULATED fire event triggered in {room.room_id}",
        actor="RESQ AI Simulation Engine",
    ))
    db.add(m.IncidentTimeline(
        incident_id=incident.incident_id,
        timestamp=datetime.utcnow(),
        event=f"Risk engine scored incident {result['risk_score']} pts ({result['risk_level']}) — factors: "
              + ", ".join(result["contributing_factors"]),
        actor="RESQ AI Risk Engine",
    ))
    db.commit()

    return {
        "message": "Simulated fire event created",
        "room_id": room.room_id,
        "incident": s.IncidentOut.model_validate(incident),
        "risk": result,
    }


@router.post("/api/simulation/reset")
def reset_demo(db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_role("admin"))):
    """
    Demo reset: wipes all data (simulated fires, rescues, dispatches, timeline)
    and reloads the original seed dataset, so the dashboard starts clean again.
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if backend_dir not in sys.path:
        sys.path.append(backend_dir)
    from seed_database import seed  # noqa: E402

    try:
        keep = {"users", "audit_logs"}          # accounts and the audit trail survive a reset
        for table in reversed(Base.metadata.sorted_tables):
            if table.name not in keep:
                db.execute(table.delete())
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Reset failed while clearing data")
    finally:
        db.close()

    seed()
    from app.database.db import SessionLocal
    audit_db = SessionLocal()
    try:
        log_action(audit_db, user, "reset_demo", detail="original dataset restored", commit=True)
    finally:
        audit_db.close()
    return {"message": "Demo reset: original dataset restored"}
