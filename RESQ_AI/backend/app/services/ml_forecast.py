"""Live inference for the ML forecast. Loads ml/model.json (trained on SYNTHETIC data) and
predicts: P(room risk score > 60 within the next 10 minutes). It never changes the observed
risk score - the rule engine stays the source of truth; this is a separate, labelled forecast."""
import json, os
from datetime import datetime, timedelta
from functools import lru_cache
from ml import gbdt
from ml.features import make_features, TREND_LAG
from app.services.risk_engine import calculate_risk

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "model.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "report.json")


@lru_cache(maxsize=1)
def load_model():
    try:
        with open(MODEL_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def model_info() -> dict:
    m = load_model()
    if not m:
        return {"available": False, "detail": "ml/model.json not found - run: python -m ml.train"}
    info = {k: m[k] for k in ("model_version", "model_type", "trained_on", "target", "horizon_minutes",
                              "decision_threshold", "features", "trained_at", "checksum")}
    info["available"] = True
    try:
        with open(REPORT_PATH) as f:
            r = json.load(f)
        info["test_metrics"] = {"data": r["data"], "auc": r["test"]["auc"], "brier": r["test"]["brier"],
                                "calibration_error": r["test"]["expected_calibration_error"],
                                "early_warning": r["early_warning_test"]["at_threshold"],
                                "all_rows": r["test"]["at_threshold"], "caveat": r["caveat"]}
    except Exception:
        pass
    return info


def _state(room, fresh_reading, temp_override=None):
    """Current state = the room's live values; CO and flame come from the latest reading only if it is fresh."""
    return {"temperature": room.temperature or 0.0, "smoke": room.smoke_level or 0.0,
            "co": (fresh_reading.co_level or 0.0) if fresh_reading else 0.0,
            "flame": bool(fresh_reading.flame_detected) if fresh_reading else False,
            "fire_status": room.fire_status, "occupants": room.occupants_count or 0,
            "exit_blocked": False}   # per-room blocked-exit state is not stored; model assumes open


def _fresh(r):
    from app import config
    return r is not None and r.timestamp is not None and (datetime.utcnow() - r.timestamp).total_seconds() / 60 <= config.STALE_MINUTES


def forecast_room(room, readings: list) -> dict:
    """readings: that room's SensorReading rows, newest first."""
    m = load_model()
    base = {"room_id": room.room_id, "sensor_status": room.sensor_status}
    if not m:
        return {**base, "available": False, "reason": "model file missing"}
    if room.sensor_status != "ok":
        return {**base, "available": False, "reason": f"no forecast: sensor data {room.sensor_status}"}
    latest = readings[0] if readings and _fresh(readings[0]) else None
    cur = _state(room, latest)
    obs = calculate_risk(cur["temperature"], cur["smoke"], cur["co"], cur["flame"], cur["fire_status"],
                         cur["occupants"], False)
    past = None
    if latest:
        target = latest.timestamp - timedelta(minutes=TREND_LAG)
        for r in readings[1:]:
            if abs((r.timestamp - target).total_seconds()) <= 120:
                past = {"temperature": r.temperature or 0.0, "smoke": r.smoke_level or 0.0, "co": r.co_level or 0.0,
                        "flame": bool(r.flame_detected), "fire_status": room.fire_status,
                        "occupants": cur["occupants"], "exit_blocked": False}
                break
    p = gbdt.predict_proba(m, make_features(cur, past))
    notes = ["synthetic-trained forecast; observed risk comes from the rule engine"]
    if not past:
        notes.append("no reading ~3 min earlier: trend features = 0, forecast less reliable")
    if not latest:
        notes.append("no fresh reading: CO/flame assumed 0")
    return {**base, "available": True, "probability": round(p, 3),
            "flagged": p >= m["decision_threshold"], "threshold": m["decision_threshold"],
            "horizon_minutes": m["horizon_minutes"], "model_version": m["model_version"],
            "trend_available": past is not None,
            "observed_score": obs["risk_score"], "observed_risk_level": obs["risk_level"],
            "note": "; ".join(notes)}
