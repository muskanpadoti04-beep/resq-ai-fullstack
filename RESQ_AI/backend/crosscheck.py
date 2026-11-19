"""
RESQ AI - consistency cross-check.
Compares what the database holds, what the API returns (= what the dashboard
shows) and what the risk engine says, then prints PASS / FAIL per rule.

Usage (from the backend folder, venv active):
    python crosscheck.py            # check the current database
    python crosscheck.py --simulate # run a few simulated fires/rescues first
"""
import sys
from fastapi.testclient import TestClient

from app.main import app
from app.database.db import SessionLocal
from app.models import models as m
from app.services.risk_engine import severity_from_risk_level

BANDS = [(30, "Safe"), (60, "Moderate"), (80, "High Risk"), (100, "Critical")]


def band(score):
    return next(name for top, name in BANDS if score <= top)


def run(simulate=False):
    c = TestClient(app)
    failures = []

    # sign in as the demo admin (skipped when the API runs with RESQ_AUTH=off)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        c.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"  -> {detail}"))
        if not ok:
            failures.append(name)

    if simulate:
        for _ in range(3):
            c.post("/api/simulation/fire")
        teams = [t for t in c.get("/api/rescue-teams").json() if t["status"] == "Standby"]
        if teams:
            c.post(f"/api/rescue-teams/{teams[0]['team_id']}/dispatch")
            c.post(f"/api/rescue-teams/{teams[0]['team_id']}/complete-rescue")

    db = SessionLocal()
    try:
        summary = c.get("/api/dashboard/summary").json()
        occupants = db.query(m.Occupant).all()
        rooms = db.query(m.Room).all()
        incidents = db.query(m.Incident).all()
        teams = db.query(m.RescueTeam).all()
        timeline = db.query(m.IncidentTimeline).all()

        # --- dashboard summary vs database ---
        at_risk = sum(1 for o in occupants if o.risk_status in ("Critical", "High Risk") and not o.is_rescued)
        check("Dashboard 'People at Risk' == occupants at risk (not rescued)",
              summary["people_at_risk"] == at_risk, f"{summary['people_at_risk']} vs {at_risk}")
        trapped = sum(1 for o in occupants if o.is_trapped)
        check("Dashboard 'Potentially Trapped' == trapped occupants",
              summary["potentially_trapped"] == trapped, f"{summary['potentially_trapped']} vs {trapped}")
        active = sum(1 for i in incidents if i.status == "active")
        check("Dashboard 'Active Incidents' == active incident rows",
              summary["active_incidents"] == active, f"{summary['active_incidents']} vs {active}")
        deployed = sum(1 for t in teams if t.status in ("En Route", "On Scene"))
        check("Dashboard 'Rescue Teams Active' == deployed teams",
              summary["active_rescue_teams"] == deployed, f"{summary['active_rescue_teams']} vs {deployed}")

        # --- risk engine consistency ---
        bad = [i.incident_id for i in incidents if band(i.risk_score) != i.risk_level]
        check("Incident risk_level matches its risk_score band", not bad, bad[:5])
        bad = [i.incident_id for i in incidents if severity_from_risk_level(i.risk_level) != i.severity]
        check("Incident severity matches its risk_level", not bad, bad[:5])

        # --- rooms vs occupants ---
        per_room = {}
        for o in occupants:
            if not o.is_rescued:
                per_room[o.room_id] = per_room.get(o.room_id, 0) + 1
        bad = [r.room_id for r in rooms if r.fire_status == "active" and per_room.get(r.room_id, 0) != r.occupants_count]
        # occupant counts only change through simulation; informational for seed data
        check("Burning rooms: occupants_count matches occupant rows", not bad, bad[:5])
        bad = [r.room_id for r in rooms if r.fire_status == "active"
               and not any(i.room_id == r.room_id and i.status == "active" for i in incidents)]
        check("Every room on fire has an active incident", not bad, bad[:5])
        bad = [o.occupant_id for o in occupants if o.is_rescued and o.is_trapped]
        check("Nobody is both rescued and trapped", not bad, bad[:5])

        # --- references ---
        incident_ids = {i.incident_id for i in incidents}
        bad = [t.id for t in timeline if t.incident_id is not None and t.incident_id not in incident_ids]
        check("Timeline entries reference existing incidents", not bad, bad[:5])
        room_ids = {r.room_id for r in rooms}
        bad = [t.team_id for t in teams if t.assigned_room and t.assigned_room not in room_ids]
        check("Rescue teams are assigned to existing rooms", not bad, bad[:5])
        bad = [t.team_id for t in teams if t.status == "Standby" and t.assigned_room]
        check("Standby teams have no assigned room", not bad, bad[:5])

        # --- uniqueness ---
        ids = [i.incident_id for i in incidents]
        check("Incident IDs are unique", len(ids) == len(set(ids)))
    finally:
        db.close()

    print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed")
    return not failures


if __name__ == "__main__":
    sys.exit(0 if run("--simulate" in sys.argv) else 1)
