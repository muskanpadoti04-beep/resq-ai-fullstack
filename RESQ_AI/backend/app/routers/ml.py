from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models import models as m
from app.services.auth import CurrentUser, require_role
from app.services import ml_forecast

router = APIRouter(prefix="/api/ml", tags=["ml"])


def _readings(db, room_id, n=12):
    return (db.query(m.SensorReading).filter(m.SensorReading.room_id == room_id)
            .order_by(m.SensorReading.timestamp.desc()).limit(n).all())


@router.get("/model-info")
def model_info():
    """Model version, target, horizon, threshold and the held-out test metrics."""
    return ml_forecast.model_info()


@router.get("/forecast")
def forecast_all(db: Session = Depends(get_db)):
    """Forecast for every room (read-only, not logged). Rooms are listed highest probability first."""
    out = [ml_forecast.forecast_room(r, _readings(db, r.room_id)) for r in db.query(m.Room).all()]
    out.sort(key=lambda f: -(f.get("probability") or -1))
    return {"model": ml_forecast.model_info().get("model_version"), "forecasts": out}


@router.post("/predict/{room_id}")
def predict(room_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(require_role("operator"))):
    """Forecast one room and record it (model_version, probability, observed risk at that time)."""
    room = db.query(m.Room).filter(m.Room.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    f = ml_forecast.forecast_room(room, _readings(db, room_id))
    if f.get("available"):
        db.add(m.MLPrediction(room_id=room_id, model_version=f["model_version"], probability=f["probability"],
                              flagged=f["flagged"], threshold=f["threshold"], observed_level=f["observed_risk_level"],
                              observed_score=f["observed_score"], requested_by=user.username))
        db.commit()
    return f


@router.get("/predictions")
def prediction_log(limit: int = 50, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_role("operator"))):
    rows = db.query(m.MLPrediction).order_by(m.MLPrediction.id.desc()).limit(min(limit, 500)).all()
    return [{"id": r.id, "time": r.created_at.isoformat(), "room_id": r.room_id, "model_version": r.model_version,
             "probability": r.probability, "flagged": r.flagged, "observed_level": r.observed_level,
             "observed_score": r.observed_score, "by": r.requested_by} for r in rows]
