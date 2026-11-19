"""
RESQ AI - Database seeding script.
Creates tables (if needed), reads the CSV datasets, and inserts records into
SQLite. Safe to re-run: existing rows (matched by natural key) are skipped.
"""
import csv
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import Base, engine, SessionLocal
from app.services.risk_engine import calculate_risk, severity_from_risk_level
from app.services.validation import validate_room, validate_occupant, validate_incident
from app.services.topology import build_topology
from app.services.auth import seed_default_users
from app.models.models import (
    Building, Floor, Room, Occupant, Incident, SensorReading,
    RescueTeam, MedicalSupport, IncidentTimeline, CameraFeed,
)

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")


def read_csv(name):
    path = os.path.join(DATASET_DIR, name)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def to_bool(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    skipped = []   # (file, row id, problems) for rows that failed validation

    try:
        # ---------------- Building ----------------
        if not db.query(Building).filter_by(building_id="BLD-01").first():
            db.add(Building(
                building_id="BLD-01",
                name="RESQ AI Command Tower",
                address="Sector 7, Demo Campus",
                total_floors=4,
            ))
            db.commit()

        # ---------------- Floors ----------------
        floor_labels = {1: "Ground Floor", 2: "1st Floor", 3: "2nd Floor", 4: "3rd Floor"}
        floor_objs = {}
        for fnum, label in floor_labels.items():
            existing = db.query(Floor).filter_by(building_id="BLD-01", floor_number=fnum).first()
            if not existing:
                existing = Floor(building_id="BLD-01", floor_number=fnum, floor_label=label)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            floor_objs[fnum] = existing

        # ---------------- Rooms ----------------
        rooms_csv = read_csv("rooms.csv")
        for row in rooms_csv:
            if db.query(Room).filter_by(room_id=row["room_id"]).first():
                continue
            problems = validate_room(row)
            if problems:
                skipped.append(("rooms.csv", row.get("room_id"), problems))
                continue
            floor_num = int(row["floor"])
            # room risk level comes from the risk engine (not the CSV label) so it cannot contradict the score
            room_risk = calculate_risk(float(row["temperature"]), float(row["smoke_level"]), 0.0,
                                       row["fire_status"] == "active", row["fire_status"], int(row["occupants"]))
            db.add(Room(
                room_id=row["room_id"],
                floor_id=floor_objs[floor_num].id,
                floor_number=floor_num,
                room_number=row["room_number"],
                capacity=int(row["capacity"]),
                occupants_count=int(row["occupants"]),
                risk_level=room_risk["risk_level"],
                temperature=float(row["temperature"]),
                smoke_level=float(row["smoke_level"]),
                fire_status=row["fire_status"],
                last_sensor_update=datetime.utcnow(),
            ))
        db.commit()
        build_topology(db)   # corridors, stairs and exits connected to the rooms

        # ---------------- Occupants ----------------
        known_rooms = {r.room_id for r in db.query(Room).all()}
        for row in read_csv("occupants.csv"):
            if db.query(Occupant).filter_by(occupant_id=row["occupant_id"]).first():
                continue
            problems = validate_occupant(row, known_rooms)
            if problems:
                skipped.append(("occupants.csv", row.get("occupant_id"), problems))
                continue
            db.add(Occupant(
                occupant_id=row["occupant_id"],
                room_id=row["room_id"],
                name=row["name"],
                type=row["type"],
                age_group=row["age_group"],
                risk_status=row["risk_status"],
                is_trapped=to_bool(row["is_trapped"]),
            ))
        db.commit()

        # ---------------- Incidents (+ seed timeline) ----------------
        for row in read_csv("incidents.csv"):
            if db.query(Incident).filter_by(incident_id=row["incident_id"]).first():
                continue
            problems = validate_incident(row, known_rooms)
            if problems:
                skipped.append(("incidents.csv", row.get("incident_id"), problems))
                continue
            detected_at = datetime.strptime(row["detected_at"], "%Y-%m-%d %H:%M:%S")
            # Risk score, risk level and severity all come from the risk engine,
            # so they can never contradict each other.
            result = calculate_risk(
                temperature=float(row["temperature"]),
                smoke_level=float(row["smoke_level"]),
                flame_detected=row["fire_status"] == "active",
                fire_status=row["fire_status"],
                occupants_count=int(row["occupants_count"]),
            )
            risk_level = result["risk_level"]
            severity = severity_from_risk_level(risk_level)
            incident = Incident(
                incident_id=row["incident_id"],
                building_id=row["building_id"],
                floor=int(row["floor"]),
                room_id=row["room"],
                incident_type=row["incident_type"],
                severity=severity,
                temperature=float(row["temperature"]),
                smoke_level=float(row["smoke_level"]),
                fire_status=row["fire_status"],
                detected_at=detected_at,
                occupants_count=int(row["occupants_count"]),
                risk_score=result["risk_score"],
                risk_level=risk_level,
                acknowledged=False,
                status="active",
                lifecycle="Detected",
            )
            db.add(incident)
            db.commit()

            db.add(IncidentTimeline(
                incident_id=incident.incident_id,
                timestamp=detected_at,
                event=f"{incident.incident_type} detected in {incident.room_id}",
                actor="RESQ AI Sensor Network",
            ))
            db.add(IncidentTimeline(
                incident_id=incident.incident_id,
                timestamp=detected_at + timedelta(minutes=1),
                event=f"Risk engine classified incident as {incident.risk_level} ({incident.risk_score} pts)",
                actor="RESQ AI Risk Engine",
            ))
        db.commit()

        # ---------------- Sensor Readings ----------------
        for row in read_csv("sensor_readings.csv"):
            if db.query(SensorReading).filter_by(reading_id=row["reading_id"]).first():
                continue
            db.add(SensorReading(
                reading_id=row["reading_id"],
                room_id=row["room_id"],
                timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                temperature=float(row["temperature"]),
                smoke_level=float(row["smoke_level"]),
                co_level=float(row["co_level"]),
                flame_detected=to_bool(row["flame_detected"]),
                humidity=float(row["humidity"]),
            ))
        db.commit()

        # ---------------- Rescue Teams ----------------
        for row in read_csv("rescue_teams.csv"):
            if db.query(RescueTeam).filter_by(team_id=row["team_id"]).first():
                continue
            db.add(RescueTeam(
                team_id=row["team_id"],
                team_name=row["team_name"],
                status=row["status"],
                current_location=row["current_location"],
                assigned_room=row["assigned_room"] or None,
                eta_minutes=float(row["eta_minutes"]) if row["eta_minutes"] else 0,
            ))
        db.commit()

        # Teams already deployed in the dataset must match the incident lifecycle:
        # link each one to the active incident in its room (or stand it down if there is none).
        for team in db.query(RescueTeam).filter(RescueTeam.status.in_(["En Route", "On Scene"])).all():
            inc = (db.query(Incident)
                   .filter(Incident.room_id == team.assigned_room, Incident.status == "active",
                           Incident.assigned_team_id.is_(None)).first())
            if not inc:
                skipped.append(("rescue_teams.csv", team.team_id,
                                [f"no active incident in {team.assigned_room}; team set to Standby"]))
                team.status, team.assigned_room, team.eta_minutes, team.current_location = "Standby", None, 0, "Base"
                continue
            inc.assigned_team_id = team.team_id
            inc.acknowledged = True
            inc.acknowledged_at = inc.detected_at + timedelta(minutes=1)
            inc.dispatched_at = inc.detected_at + timedelta(minutes=2)
            inc.en_route_at = inc.dispatched_at
            inc.lifecycle = "En Route"
            if team.status == "On Scene":
                inc.on_scene_at = inc.dispatched_at + timedelta(minutes=4)
                inc.lifecycle = "On Scene"
        db.commit()

        # ---------------- Medical Support (synthetic, no separate CSV requested) ----------------
        if db.query(MedicalSupport).count() == 0:
            medical_units = [
                ("MED-01", "Paramedic Unit 1", "En Route", 2, 4),
                ("MED-02", "Paramedic Unit 2", "Standby", 2, 0),
                ("MED-03", "Trauma Response Team", "On Scene", 3, 0),
            ]
            critical_room = db.query(Room).filter(Room.risk_level == "Critical").first()
            for uid, name, status, personnel, eta in medical_units:
                db.add(MedicalSupport(
                    unit_id=uid,
                    unit_name=name,
                    status=status,
                    assigned_room=critical_room.room_id if (status != "Standby" and critical_room) else None,
                    personnel_count=personnel,
                    eta_minutes=eta,
                ))
            db.commit()

        # ---------------- Camera Feeds (synthetic, one per room) ----------------
        if db.query(CameraFeed).count() == 0:
            rooms = db.query(Room).all()
            for r in rooms:
                db.add(CameraFeed(
                    camera_id=f"CAM-{r.room_id}",
                    room_id=r.room_id,
                    label=f"Camera - {r.room_id}",
                    status="online",
                    stream_status="simulated",   # no real video exists in this prototype
                    last_seen=datetime.utcnow(),
                ))
            db.commit()

        seed_default_users(db)

        # ---------------- Summary ----------------
        print("Database seeded successfully")
        if skipped:
            print()
            print(f"Validation: {len(skipped)} item(s) skipped or adjusted:")
            for src, rid, problems in skipped:
                print(f"  - {src} {rid}: " + "; ".join(problems))
        print()
        print(f"Buildings: {db.query(Building).count()}")
        print(f"Floors: {db.query(Floor).count()}")
        print(f"Rooms: {db.query(Room).count()}")
        print(f"Occupants: {db.query(Occupant).count()}")
        print(f"Incidents: {db.query(Incident).count()}")
        print(f"Sensor readings: {db.query(SensorReading).count()}")
        print(f"Rescue teams: {db.query(RescueTeam).count()}")
        print(f"Medical support units: {db.query(MedicalSupport).count()}")
        print(f"Camera feeds: {db.query(CameraFeed).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
