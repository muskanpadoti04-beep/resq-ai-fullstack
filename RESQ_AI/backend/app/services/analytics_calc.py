"""
RESQ AI - analytics calculations (pure Python: no database or web imports, so they are easy to test).
Save as backend/app/services/analytics_calc.py
"""
from datetime import datetime, timedelta
from typing import Optional

RISK_LEVELS = ["Safe", "Moderate", "High Risk", "Critical"]
SEVERITIES = ["Critical", "High", "Moderate", "Low"]


def iso_z(dt: Optional[datetime]) -> Optional[str]:
    """Backend times are UTC without a zone; adding Z lets the browser show the viewer's local time."""
    return dt.isoformat() + "Z" if dt else None


def minutes_between(a: Optional[datetime], b: Optional[datetime]) -> Optional[float]:
    if a is None or b is None or b < a:
        return None
    return round((b - a).total_seconds() / 60, 1)


def average(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def build_summary(incidents, occupants, rooms, floors, now: datetime) -> dict:
    active = [i for i in incidents if i.status == "active"]
    resolved = [i for i in incidents if i.status == "resolved"]

    # ---- response times, measured from the incident timestamps ----
    assign = [minutes_between(i.detected_at, i.dispatched_at) for i in incidents]
    travel = [minutes_between(i.en_route_at or i.dispatched_at, i.on_scene_at) for i in incidents]
    rescue = [minutes_between(i.on_scene_at, i.resolved_at) for i in incidents]
    total = [minutes_between(i.detected_at, i.resolved_at) for i in incidents]

    recent = sorted([i for i in incidents if i.dispatched_at is not None], key=lambda i: i.detected_at)[-8:]
    breakdown = []
    for i in recent:
        a = minutes_between(i.detected_at, i.dispatched_at)
        t = minutes_between(i.en_route_at or i.dispatched_at, i.on_scene_at)
        r = minutes_between(i.on_scene_at, i.resolved_at)
        breakdown.append({
            "incident_id": i.incident_id, "room_id": i.room_id, "status": i.status,
            "assign_min": a or 0, "travel_min": t or 0, "rescue_min": r or 0,
        })

    # ---- people ----
    inside = [o for o in occupants if not o.is_rescued]
    rescued = [o for o in occupants if o.is_rescued]
    at_risk = [o for o in inside if o.is_trapped or o.risk_status in ("Critical", "High Risk")]
    people = [
        {"status": "Safe", "count": sum(1 for o in inside if o.risk_status == "Safe" and not o.is_trapped)},
        {"status": "High Risk", "count": sum(1 for o in inside if o.risk_status == "High Risk")},
        {"status": "Critical", "count": sum(1 for o in inside if o.risk_status == "Critical")},
        {"status": "Rescued", "count": len(rescued)},
    ]

    # ---- rooms by risk level, per floor ----
    floor_label = {f.floor_number: f.floor_label for f in floors}
    numbers = sorted(set(floor_label) | {r.floor_number for r in rooms})
    by_floor = []
    for n in numbers:
        row = {"floor": n, "label": floor_label.get(n, f"Floor {n}")}
        for lvl in RISK_LEVELS:
            row[lvl] = sum(1 for r in rooms if r.floor_number == n and (r.risk_level if r.risk_level in RISK_LEVELS else "Safe") == lvl)
        row["active_incidents"] = sum(1 for i in active if i.floor == n)
        by_floor.append(row)

    # ---- incidents opened / resolved per hour, last 12 hours ----
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=11)
    timeline = []
    for k in range(12):
        lo = start + timedelta(hours=k)
        hi = lo + timedelta(hours=1)
        timeline.append({
            "hour": iso_z(lo),
            "opened": sum(1 for i in incidents if i.detected_at and lo <= i.detected_at < hi),
            "resolved": sum(1 for i in incidents if i.resolved_at and lo <= i.resolved_at < hi),
        })

    severity = [{"severity": s, "count": sum(1 for i in incidents if i.severity == s)} for s in SEVERITIES]

    return {
        "kpis": {
            "active_incidents": len(active),
            "resolved_incidents": len(resolved),
            "avg_assign_min": average(assign),
            "avg_travel_min": average(travel),
            "avg_rescue_min": average(rescue),
            "avg_total_min": average(total),
            "people_inside": len(inside),
            "people_at_risk": len(at_risk),
            "people_trapped": sum(1 for o in inside if o.is_trapped),
            "people_rescued": len(rescued),
            "humans_rescued": sum(1 for o in rescued if o.type == "Human"),
            "animals_rescued": sum(1 for o in rescued if o.type != "Human"),
        },
        "response_breakdown": breakdown,
        "people": people,
        "by_floor": by_floor,
        "timeline": timeline,
        "severity": severity,
    }


def pick_default_room(rooms, incidents) -> Optional[str]:
    """Room to show first in the sensor chart: the active incident with the highest score, else the hottest room."""
    active = [i for i in incidents if i.status == "active"]
    if active:
        return max(active, key=lambda i: i.risk_score or 0).room_id
    hot = [r for r in rooms if r.temperature is not None]
    if hot:
        return max(hot, key=lambda r: r.temperature).room_id
    return rooms[0].room_id if rooms else None


def downsample(points: list, max_points: int) -> list:
    if len(points) <= max_points:
        return points
    step = -(-len(points) // max_points)          # ceiling division
    out = points[::step]
    if out[-1] is not points[-1]:
        out.append(points[-1])                    # always keep the newest reading
    return out
