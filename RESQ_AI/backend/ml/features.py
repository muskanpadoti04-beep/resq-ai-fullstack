"""Shared feature definition for the ML forecast (used by training AND live inference).

TARGET   : will this room's rule-engine risk score exceed 60 (High Risk or Critical)
           at ANY point in the next HORIZON_MIN minutes?
HORIZON  : 10 minutes. Readings are 1 per minute.
"""
import math
from app.services.risk_engine import calculate_risk

HORIZON_MIN = 10
POSITIVE_SCORE = 60          # label = 1 if future score > 60
TREND_LAG = 3                # minutes used for trend features
FIRE_CODE = {"none": 0.0, "smoke": 1.0, "contained": 1.0, "active": 2.0}

FEATURE_NAMES = [
    "temperature", "smoke", "co", "flame", "fire_code", "occupants", "exit_blocked",
    "d_temp_3m", "d_smoke_3m", "d_co_3m", "rule_score", "d_rule_score_3m",
]


def make_features(cur: dict, past: dict | None) -> list[float]:
    """cur/past: dicts with temperature, smoke, co, flame(bool), fire_status, occupants, exit_blocked.
    past = the reading TREND_LAG minutes earlier (None -> trends 0, i.e. 'no history')."""
    p = past or cur
    sc = lambda r: calculate_risk(r["temperature"], r["smoke"], r["co"], r["flame"], r["fire_status"],
                                  r["occupants"], r["exit_blocked"])["risk_score"]
    now_score = sc(cur)
    return [
        float(cur["temperature"]), float(cur["smoke"]), float(cur["co"]),
        1.0 if cur["flame"] else 0.0, FIRE_CODE.get(cur["fire_status"], 0.0),
        float(min(cur["occupants"], 10)), 1.0 if cur["exit_blocked"] else 0.0,
        float(cur["temperature"] - p["temperature"]),
        float(cur["smoke"] - p["smoke"]),
        float(cur["co"] - p["co"]),
        now_score, now_score - sc(p),
    ]


def sigmoid(z: float) -> float:
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))
