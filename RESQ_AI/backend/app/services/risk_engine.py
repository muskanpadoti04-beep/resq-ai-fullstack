"""
RESQ AI - Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination
AI-Assisted Fire Risk Scoring Engine

NOTE: This is a transparent, rule-based scoring engine built for prototype /
demonstration purposes. It is NOT a trained machine-learning model. It is
called "AI-assisted" because it encodes domain heuristics (the kind a fire
safety expert system would use) to produce an explainable, weighted risk
score with human-readable contributing factors.
"""
from typing import Optional


def severity_from_risk_level(risk_level: str) -> str:
    """Single source of truth: incident severity always follows the risk score band."""
    return {"Critical": "Critical", "High Risk": "High", "Moderate": "Moderate"}.get(risk_level, "Low")


def level_from_score(score: float) -> str:
    """Single source of truth for the score -> band mapping."""
    if score <= 30:
        return "Safe"
    if score <= 60:
        return "Moderate"
    if score <= 80:
        return "High Risk"
    return "Critical"


# (rule id, predicate(temp, smoke, co, flame, fire_status), minimum score, human reason)
# Floors: 61 = lowest "High Risk" score, 81 = lowest "Critical" score.
OVERRIDE_RULES = [
    ("FLAME_AND_ACTIVE_FIRE", lambda t, s, c, fl, fs: fl and fs == "active", 81,
     "flame confirmed and fire status active -> minimum Critical"),
    ("CO_LETHAL", lambda t, s, c, fl, fs: c >= 200, 81,
     "CO >= 200 ppm is life-threatening -> minimum Critical"),
    ("ACTIVE_FIRE", lambda t, s, c, fl, fs: fs == "active", 61,
     "fire status active -> minimum High Risk"),
    ("FLAME_DETECTED", lambda t, s, c, fl, fs: fl, 61,
     "flame detected -> minimum High Risk"),
    ("EXTREME_HEAT", lambda t, s, c, fl, fs: t >= 120, 61,
     "temperature >= 120 C -> minimum High Risk"),
]


def calculate_risk(
    temperature: Optional[float],
    smoke_level: Optional[float],
    co_level: Optional[float] = 0.0,
    flame_detected: bool = False,
    fire_status: str = "none",
    occupants_count: int = 0,
    exit_blocked: bool = False,
) -> dict:
    """
    Calculates a 0-100 fire risk score from live sensor + situational inputs.

    Weighted components:
      temperature risk   -> up to 25 points
      smoke risk         -> up to 25 points
      CO risk             -> up to 15 points
      fire status risk   -> up to 20 points
      occupancy risk      -> up to 10 points
      blocked exit risk  -> up to 5 points

    Then emergency override rules (OVERRIDE_RULES) may raise the score to a minimum
    floor. Overrides only ever raise the score, never lower it. The result includes
    score_breakdown (points per factor), weighted_score (before overrides) and
    overrides_applied so every number can be explained.
    """
    factors = []
    missing = []  # sensors that sent no data: they add 0 points, and we say so explicitly

    # --- Temperature risk (normal ~20-25C, danger > 60C) ---
    if temperature is None:
        missing.append("temperature")
        temperature = 0.0
        temp_risk = 0.0
    else:
        temp_risk = min(max((temperature - 25) / (150 - 25), 0), 1) * 25
    if temperature >= 80:
        factors.append("High temperature")
    elif temperature >= 45:
        factors.append("Elevated temperature")

    # --- Smoke risk (0-100 scale sensor reading assumed) ---
    if smoke_level is None:
        missing.append("smoke")
        smoke_level = 0.0
    smoke_risk = min(max(smoke_level, 0), 100) / 100 * 25
    if smoke_level >= 70:
        factors.append("High smoke level")
    elif smoke_level >= 35:
        factors.append("Moderate smoke detected")

    # --- CO risk (ppm, danger > 150) ---
    if co_level is None:
        missing.append("CO")
        co_level = 0.0
    co_risk = min(max(co_level, 0), 200) / 200 * 15
    if co_level >= 100:
        factors.append("Dangerous CO level")
    elif co_level >= 50:
        factors.append("Elevated CO level")

    # --- Fire status risk ---
    fire_status_map = {"none": 0.0, "smoke": 0.4, "active": 1.0, "contained": 0.5}
    fire_risk = fire_status_map.get(fire_status, 0.0) * 20
    if flame_detected or fire_status == "active":
        factors.append("Fire spreading" if fire_status == "active" else "Flame detected")
    elif fire_status == "contained":
        factors.append("Fire contained but active")

    # --- Occupancy risk ---
    occ_risk = min(occupants_count, 10) / 10 * 10
    if occupants_count > 0:
        factors.append(f"{occupants_count} occupant(s) detected")

    # --- Blocked exit risk ---
    exit_risk = 5.0 if exit_blocked else 0.0
    if exit_blocked:
        factors.append("Exit blocked")

    breakdown = {
        "temperature": round(temp_risk, 1),
        "smoke": round(smoke_risk, 1),
        "co": round(co_risk, 1),
        "fire_status": round(fire_risk, 1),
        "occupancy": round(occ_risk, 1),
        "blocked_exit": round(exit_risk, 1),
    }
    weighted_score = round(min(max(temp_risk + smoke_risk + co_risk + fire_risk + occ_risk + exit_risk, 0), 100), 1)

    # --- Emergency override rules: a weighted sum can under-rate a real emergency
    # (e.g. confirmed flame but a cool, smoke-free reading). Each rule sets a MINIMUM score.
    overrides = []
    for rule_id, hit, floor, why in OVERRIDE_RULES:
        if hit(temperature, smoke_level, co_level, flame_detected, fire_status):
            overrides.append({"rule": rule_id, "floor": floor, "reason": why})
    risk_score = weighted_score
    if overrides:
        risk_score = max(weighted_score, max(o["floor"] for o in overrides))
    risk_score = round(risk_score, 1)
    risk_level = level_from_score(risk_score)
    if overrides and risk_score > weighted_score:
        top = max(overrides, key=lambda o: o["floor"])   # one line in the factor list; all stay in overrides_applied
        factors.append(f"OVERRIDE: {top['reason']}")

    for name in missing:
        factors.append(f"{name} sensor data missing - score may be understated")
    if not factors:
        factors.append("No significant hazards detected")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "contributing_factors": factors,
        "data_quality": "partial" if missing else "complete",
        "score_breakdown": breakdown,
        "weighted_score": weighted_score,
        "overrides_applied": [o for o in overrides if o["floor"] > weighted_score],
    }
