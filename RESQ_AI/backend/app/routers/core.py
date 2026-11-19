"""
RESQ AI - core routers: dashboard summary, buildings, floors, rooms, occupants
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import topology as topo
from app.services.audit import log_action
from app.services.auth import CurrentUser, require_role
from app.services.ingest import ingest_reading, IngestError

router = APIRouter(tags=["Core"])


@router.get("/api/dashboard/summary", response_model=s.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    active_incidents = db.query(m.Incident).filter(m.Incident.status == "active").count()
    people_at_risk = db.query(m.Occupant).filter(
        m.Occupant.risk_status.in_(["Critical", "High Risk"]),
        m.Occupant.is_rescued == False,  # noqa: E712
    ).count()
    potentially_trapped = db.query(m.Occupant).filter(m.Occupant.is_trapped == True).count()  # noqa: E712
    active_rescue_teams = db.query(m.RescueTeam).filter(
        m.RescueTeam.status.in_(["En Route", "On Scene"])
    ).count()
    available_exits = topo.exits_available(db)["available"]  # from the building graph
    medical_support = db.query(m.MedicalSupport).filter(
        m.MedicalSupport.status.in_(["En Route", "On Scene"])
    ).count()

    return s.DashboardSummary(
        active_incidents=active_incidents,
        people_at_risk=people_at_risk,
        potentially_trapped=potentially_trapped,
        active_rescue_teams=active_rescue_teams,
        available_exits=available_exits,
        medical_support=medical_support,
    )


@router.get("/api/buildings", response_model=List[s.BuildingOut])
def get_buildings(db: Session = Depends(get_db)):
    return db.query(m.Building).all()


@router.get("/api/floors", response_model=List[s.FloorOut])
def get_floors(db: Session = Depends(get_db)):
    return db.query(m.Floor).order_by(m.Floor.floor_number).all()


@router.get("/api/rooms", response_model=List[s.RoomOut])
def get_rooms(db: Session = Depends(get_db)):
    return db.query(m.Room).order_by(m.Room.floor_number, m.Room.room_number).all()


@router.get("/api/rooms/{room_id}", response_model=s.RoomOut)
def get_room(room_id: str, db: Session = Depends(get_db)):
    room = db.query(m.Room).filter(m.Room.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.get("/api/occupants", response_model=List[s.OccupantOut])
def get_occupants(db: Session = Depends(get_db)):
    return db.query(m.Occupant).all()


@router.post("/api/rooms/{room_id}/sensor-reading")
def ingest_sensor_reading(room_id: str, payload: s.SensorReadingIn, db: Session = Depends(get_db),
                          user: CurrentUser = Depends(require_role("operator"))):
    """
    Receive one sensor reading for a room (the common entry point for simulated, uploaded
    or - later - real sensor data). A sensor that sent nothing may be null: the room is then
    flagged 'missing' instead of silently looking safe.
    """
    room = db.query(m.Room).filter(m.Room.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    try:
        result = ingest_reading(db, room, temperature=payload.temperature, smoke_level=payload.smoke_level,
                                co_level=payload.co_level, humidity=payload.humidity,
                                flame_detected=payload.flame_detected, source="api")
    except IngestError as e:
        raise HTTPException(status_code=422, detail=str(e))
    log_action(db, user, "sensor_reading", target=room_id,
               detail=f"risk {result['risk_score']} ({result['risk_level']}), data {result['data_quality']}")
    db.commit()
    return {"room_id": room_id, "risk": result, "sensor_status": room.sensor_status,
            "incident_id": result["incident_id"]}
