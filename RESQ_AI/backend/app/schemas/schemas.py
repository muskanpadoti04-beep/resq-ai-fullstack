"""
RESQ AI - Pydantic response / request schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OrmBase(BaseModel):
    class Config:
        from_attributes = True


# ---------- Building / Floor / Room ----------

class BuildingOut(OrmBase):
    building_id: str
    name: str
    address: Optional[str]
    total_floors: int


class FloorOut(OrmBase):
    building_id: str
    floor_number: int
    floor_label: str


class RoomOut(OrmBase):
    room_id: str
    floor_number: int
    room_number: str
    capacity: int
    occupants_count: int
    risk_level: str
    temperature: Optional[float] = None
    smoke_level: Optional[float] = None
    fire_status: str
    sensor_status: str = "ok"          # ok | stale | missing
    last_sensor_update: Optional[datetime] = None


# ---------- Occupant ----------

class OccupantOut(OrmBase):
    occupant_id: str
    room_id: str
    name: str
    type: str
    age_group: str
    risk_status: str
    is_trapped: bool
    is_rescued: bool = False


# ---------- Incident ----------

class IncidentOut(OrmBase):
    incident_id: str
    building_id: str
    floor: int
    room_id: str
    incident_type: str
    severity: str
    temperature: float
    smoke_level: float
    fire_status: str
    detected_at: datetime
    occupants_count: int
    risk_score: float
    risk_level: str
    acknowledged: bool
    dispatched_at: Optional[datetime] = None
    status: str
    lifecycle: str = "Detected"
    acknowledged_at: Optional[datetime] = None
    assigned_team_id: Optional[str] = None
    en_route_at: Optional[datetime] = None
    on_scene_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ---------- Rescue Team / Medical ----------

class RescueTeamOut(OrmBase):
    team_id: str
    team_name: str
    status: str
    current_location: str
    assigned_room: Optional[str]
    eta_minutes: float


class MedicalSupportOut(OrmBase):
    unit_id: str
    unit_name: str
    status: str
    assigned_room: Optional[str]
    personnel_count: int
    eta_minutes: float


# ---------- Timeline / Camera ----------

class TimelineOut(OrmBase):
    incident_id: Optional[str] = None
    timestamp: datetime
    event: str
    actor: str


class CameraOut(OrmBase):
    camera_id: str
    room_id: str
    label: str
    status: str                      # device: online / offline
    stream_status: str = "unknown"   # stream: live / no_signal / simulated
    last_seen: Optional[datetime] = None


class CameraStatusIn(BaseModel):
    device_status: Optional[str] = Field(None, pattern="^(online|offline)$")
    stream_status: Optional[str] = Field(None, pattern="^(live|no_signal|simulated)$")


# ---------- Dashboard / analytics ----------

class DashboardSummary(BaseModel):
    active_incidents: int
    people_at_risk: int
    potentially_trapped: int
    active_rescue_teams: int
    available_exits: int
    medical_support: int


class RiskCalculateRequest(BaseModel):
    # None = that sensor sent no data (handled explicitly by the risk engine)
    temperature: Optional[float] = Field(None, ge=-40, le=1200)
    smoke_level: Optional[float] = Field(None, ge=0, le=100)
    co_level: Optional[float] = Field(0.0, ge=0, le=1000)
    flame_detected: bool = False
    fire_status: str = Field("none", pattern="^(none|smoke|active|contained)$")
    occupants_count: int = Field(0, ge=0, le=10000)
    exit_blocked: bool = False


class RiskCalculateResponse(BaseModel):
    risk_score: float
    risk_level: str
    contributing_factors: List[str]
    data_quality: str = "complete"
    score_breakdown: dict = {}
    weighted_score: Optional[float] = None
    overrides_applied: List[dict] = []


# ---------- Auth / audit / topology / sensors ----------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    full_name: Optional[str] = None


class AuditLogOut(OrmBase):
    id: int
    timestamp: datetime
    username: str
    role: str
    action: str
    target: Optional[str] = None
    detail: Optional[str] = None
    success: bool


class BlockRequest(BaseModel):
    blocked: bool
    reason: Optional[str] = Field(None, max_length=200)


class SensorReadingIn(BaseModel):
    """One reading from a sensor (or the future sensor adapter). Missing sensors may be null."""
    temperature: Optional[float] = Field(None, ge=-40, le=1200)
    smoke_level: Optional[float] = Field(None, ge=0, le=100)
    co_level: Optional[float] = Field(None, ge=0, le=1000)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    flame_detected: bool = False


class SensorIngestItem(SensorReadingIn):
    room_id: str = Field(..., min_length=1, max_length=32)


class SensorBatchIn(BaseModel):
    readings: List[SensorIngestItem] = Field(..., min_length=1, max_length=500)
