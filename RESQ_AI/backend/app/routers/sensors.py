"""Sensor adapter API: the one front door for sensor data (device gateway, batch, CSV import)."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services.audit import log_action
from app.services.auth import CurrentUser, operator_or_device
from app.services.ingest import ingest_reading, IngestError

router = APIRouter(prefix="/api/sensors", tags=["Sensor adapter"])
# Kept (empty) so main.py's include_router(...camera_router) line does not break.
# Once you delete that line from main.py you can delete this one too.
camera_router = APIRouter(tags=["Sensor adapter"])

CSV_MAX_ROWS = 5000
TRUE = {"1", "true", "yes", "y", "t"}


def _blank(v):
    return None if v is None or str(v).strip() == "" else v


def _float(v):
    v = _blank(v)
    return None if v is None else float(v)


def _process(db, items, source):
    """items: iterable of (label, callable returning kwargs). One bad item never blocks the rest."""
    accepted, rejected = [], []
    rooms = {r.room_id: r for r in db.query(m.Room).all()}
    for label, get in items:
        try:
            kw = get()
            room = rooms.get(kw.pop("room_id"))
            if room is None:
                raise IngestError("unknown room_id")
            with db.begin_nested():              # a failed row rolls back only itself
                accepted.append(ingest_reading(db, room, source=source, **kw))
        except (IngestError, ValueError, KeyError) as e:
            rejected.append({"item": label, "reason": str(e) or "invalid"})
    return accepted, rejected


@router.post("/ingest")
def ingest_batch(payload: s.SensorBatchIn, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(operator_or_device)):
    """Batch of readings (max 500). Auth: operator login OR X-Device-Key header.
    A null sensor value means 'that sensor sent nothing' (flagged, never treated as safe)."""
    items = [(f"#{i}:{r.room_id}", (lambda r=r: {**r.model_dump()})) for i, r in enumerate(payload.readings)]
    accepted, rejected = _process(db, items, "api")
    log_action(db, user, "sensor_ingest", detail=f"{len(accepted)} accepted, {len(rejected)} rejected")
    db.commit()
    return {"accepted": len(accepted), "rejected": len(rejected), "results": accepted, "errors": rejected}


@router.post("/import-csv")
async def import_csv(request: Request, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(operator_or_device)):
    """Send raw CSV as the request body (Content-Type: text/csv). Header row required:
    room_id,temperature,smoke_level,co_level,humidity,flame_detected  (empty cell = sensor missing)."""
    raw = (await request.body()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    need = {"room_id", "temperature", "smoke_level"}
    if not reader.fieldnames or not need.issubset({f.strip() for f in reader.fieldnames}):
        raise HTTPException(status_code=422, detail="CSV needs a header row with at least: room_id,temperature,smoke_level")
    rows = []
    for i, row in enumerate(reader, start=2):          # line 1 = header
        if i - 1 > CSV_MAX_ROWS:
            raise HTTPException(status_code=413, detail=f"CSV has more than {CSV_MAX_ROWS} rows")
        row = {(k or "").strip(): v for k, v in row.items()}
        rows.append((f"line {i}", (lambda row=row: {
            "room_id": (row.get("room_id") or "").strip(),
            "temperature": _float(row.get("temperature")), "smoke_level": _float(row.get("smoke_level")),
            "co_level": _float(row.get("co_level")), "humidity": _float(row.get("humidity")),
            "flame_detected": str(row.get("flame_detected") or "").strip().lower() in TRUE})))
    accepted, rejected = _process(db, rows, "csv")
    log_action(db, user, "sensor_csv_import", detail=f"{len(accepted)} accepted, {len(rejected)} rejected")
    db.commit()
    return {"accepted": len(accepted), "rejected": len(rejected), "errors": rejected[:50],
            "incidents_opened": [a["incident_id"] for a in accepted if a["incident_opened"]]}