"""
RESQ AI - Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination
SQLAlchemy ORM models
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database.db import Base
from app import config


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, unique=True, index=True)
    name = Column(String)
    address = Column(String)
    total_floors = Column(Integer)

    floors = relationship("Floor", back_populates="building", cascade="all, delete-orphan")


class Floor(Base):
    __tablename__ = "floors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, ForeignKey("buildings.building_id"))
    floor_number = Column(Integer)
    floor_label = Column(String)  # e.g. "3rd Floor"

    building = relationship("Building", back_populates="floors")
    rooms = relationship("Room", back_populates="floor", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True)
    floor_id = Column(Integer, ForeignKey("floors.id"))
    floor_number = Column(Integer)
    room_number = Column(String)
    capacity = Column(Integer, default=0)
    occupants_count = Column(Integer, default=0)
    risk_level = Column(String, default="Safe")
    temperature = Column(Float, default=22.0)
    smoke_level = Column(Float, default=0.0)
    fire_status = Column(String, default="none")  # none, smoke, active, contained
    last_sensor_update = Column(DateTime, nullable=True)  # when this room last reported sensor data

    @property
    def sensor_status(self) -> str:
        """ok | stale | missing - so old or absent sensor data is never shown as a normal reading."""
        if self.temperature is None or self.smoke_level is None or self.last_sensor_update is None:
            return "missing"
        age_min = (datetime.utcnow() - self.last_sensor_update).total_seconds() / 60
        return "stale" if age_min > config.STALE_MINUTES else "ok"

    floor = relationship("Floor", back_populates="rooms")
    occupants = relationship("Occupant", back_populates="room", cascade="all, delete-orphan")
    sensor_readings = relationship("SensorReading", back_populates="room", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="room", cascade="all, delete-orphan")
    cameras = relationship("CameraFeed", back_populates="room", cascade="all, delete-orphan")


class Occupant(Base):
    __tablename__ = "occupants"

    id = Column(Integer, primary_key=True, index=True)
    occupant_id = Column(String, unique=True, index=True)
    room_id = Column(String, ForeignKey("rooms.room_id"))
    name = Column(String)
    type = Column(String, default="Human")  # Human, Dog
    age_group = Column(String, default="Adult")
    risk_status = Column(String, default="Safe")  # Critical, High Risk, Safe
    is_trapped = Column(Boolean, default=False)
    is_rescued = Column(Boolean, default=False)  # set when a rescue team completes a rescue

    room = relationship("Room", back_populates="occupants")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, unique=True, index=True)
    building_id = Column(String)
    floor = Column(Integer)
    room_id = Column(String, ForeignKey("rooms.room_id"))
    incident_type = Column(String, default="Fire")
    severity = Column(String, default="Moderate")
    temperature = Column(Float, default=0.0)
    smoke_level = Column(Float, default=0.0)
    fire_status = Column(String, default="none")
    detected_at = Column(DateTime, default=datetime.utcnow)
    occupants_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="Safe")
    acknowledged = Column(Boolean, default=False)
    dispatched_at = Column(DateTime, nullable=True)  # first rescue dispatch (for response-time metric)
    status = Column(String, default="active")  # active, resolved
    # Lifecycle: Detected -> Acknowledged -> Assigned -> En Route -> On Scene -> Resolved
    lifecycle = Column(String, default="Detected")
    acknowledged_at = Column(DateTime, nullable=True)
    assigned_team_id = Column(String, nullable=True)
    en_route_at = Column(DateTime, nullable=True)
    on_scene_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    room = relationship("Room", back_populates="incidents")
    timeline_events = relationship("IncidentTimeline", back_populates="incident", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    reading_id = Column(String, unique=True, index=True)
    room_id = Column(String, ForeignKey("rooms.room_id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float)
    smoke_level = Column(Float)
    co_level = Column(Float)
    flame_detected = Column(Boolean, default=False)
    humidity = Column(Float)

    room = relationship("Room", back_populates="sensor_readings")


class RescueTeam(Base):
    __tablename__ = "rescue_teams"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(String, unique=True, index=True)
    team_name = Column(String)
    status = Column(String, default="Standby")  # Standby, En Route, On Scene
    current_location = Column(String)
    assigned_room = Column(String, ForeignKey("rooms.room_id"), nullable=True)
    eta_minutes = Column(Float, default=0)


class MedicalSupport(Base):
    __tablename__ = "medical_support"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String, unique=True, index=True)
    unit_name = Column(String)
    status = Column(String, default="Standby")
    assigned_room = Column(String, nullable=True)
    personnel_count = Column(Integer, default=2)
    eta_minutes = Column(Float, default=0)


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, ForeignKey("incidents.incident_id"), nullable=True)  # None = not tied to an incident
    timestamp = Column(DateTime, default=datetime.utcnow)
    event = Column(String)
    actor = Column(String, default="System")

    incident = relationship("Incident", back_populates="timeline_events")


class CameraFeed(Base):
    __tablename__ = "camera_feeds"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, unique=True, index=True)
    room_id = Column(String, ForeignKey("rooms.room_id"))
    label = Column(String)
    status = Column(String, default="online")  # DEVICE status: online, offline (is the camera itself alive?)
    stream_status = Column(String, default="simulated")  # STREAM status: live, no_signal, simulated (is video arriving?)
    last_seen = Column(DateTime, nullable=True)

    room = relationship("Room", back_populates="cameras")


class TopologyNode(Base):
    """A point in the building graph: a room, a corridor segment, a stairwell or an exit."""
    __tablename__ = "topology_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True)   # e.g. R:2B-204, C:2:W, S:A:2, X:A
    node_type = Column(String)                          # room | corridor | stair | exit
    floor_number = Column(Integer)
    room_id = Column(String, ForeignKey("rooms.room_id"), nullable=True)
    label = Column(String)
    blocked = Column(Boolean, default=False)            # set by an operator (e.g. exit blocked)
    blocked_reason = Column(String, nullable=True)


class TopologyEdge(Base):
    """A walkable connection between two nodes (usable in both directions)."""
    __tablename__ = "topology_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_node = Column(String, ForeignKey("topology_nodes.node_id"))
    to_node = Column(String, ForeignKey("topology_nodes.node_id"))
    length_m = Column(Float, default=5.0)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    password_hash = Column(String)
    role = Column(String, default="viewer")             # viewer | operator | admin
    active = Column(Boolean, default=True)


class AuditLog(Base):
    """Append-only record of who did what (login, dispatch, acknowledge, simulate, reset...)."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String)
    role = Column(String)
    action = Column(String, index=True)
    target = Column(String, nullable=True)
    detail = Column(String, nullable=True)
    success = Column(Boolean, default=True)


class MLPrediction(Base):
    """Every logged ML forecast, with the model version that made it (for audit and later evaluation)."""
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    room_id = Column(String, ForeignKey("rooms.room_id"), index=True)
    model_version = Column(String, index=True)
    probability = Column(Float)
    flagged = Column(Boolean)
    threshold = Column(Float)
    observed_level = Column(String)      # rule-engine level at prediction time
    observed_score = Column(Float)
    requested_by = Column(String)


class Notification(Base):
    """Alerts raised by the system (new incident, escalation...). Channel is the dashboard today;
    SMS/e-mail/push would be added as extra channels without changing this table."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String, default="info")          # info | warning | critical
    kind = Column(String, index=True)               # new_incident | escalation | sensor_fault | ...
    incident_id = Column(String, nullable=True, index=True)
    room_id = Column(String, nullable=True)
    message = Column(String)
    escalation_level = Column(Integer, default=0)
    channel = Column(String, default="dashboard")
    read = Column(Boolean, default=False)
