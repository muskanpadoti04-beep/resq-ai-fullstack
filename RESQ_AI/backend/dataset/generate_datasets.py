"""
RESQ AI - synthetic dataset generator (run once to (re)create the CSVs).
All data is fictional / synthetic, for prototype demonstration only.
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

HERE = os.path.dirname(os.path.abspath(__file__))

BUILDING_ID = "BLD-01"
FLOORS = [1, 2, 3, 4]
FLOOR_LABELS = {1: "Ground Floor", 2: "1st Floor", 3: "2nd Floor", 4: "3rd Floor"}
ROOMS_PER_FLOOR = ["A-101", "A-102", "B-201", "B-202", "B-203", "B-204"]

FIRST_NAMES = ["Aarav", "Vivaan", "Isha", "Diya", "Kabir", "Anaya", "Reyansh",
               "Myra", "Aditya", "Sara", "Vihaan", "Ira", "Arjun", "Kiara",
               "Rohan", "Meera", "Karan", "Tara", "Yash", "Nisha"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Gupta", "Singh", "Rao", "Kulkarni",
              "Mishra", "Nair", "Reddy"]

# ---------------- rooms.csv ----------------
rooms = []
room_ids = []
for floor in FLOORS:
    for rn in ROOMS_PER_FLOOR:
        room_id = f"{floor}{rn}"
        room_ids.append((room_id, floor, rn))

for i, (room_id, floor, rn) in enumerate(room_ids):
    risk_roll = random.random()
    if risk_roll > 0.9:
        risk_level, fire_status, temp, smoke = "Critical", "active", random.uniform(85, 140), random.uniform(70, 100)
    elif risk_roll > 0.75:
        risk_level, fire_status, temp, smoke = "High Risk", "smoke", random.uniform(45, 80), random.uniform(35, 65)
    elif risk_roll > 0.55:
        risk_level, fire_status, temp, smoke = "Moderate", "none", random.uniform(28, 40), random.uniform(5, 30)
    else:
        risk_level, fire_status, temp, smoke = "Safe", "none", random.uniform(20, 27), random.uniform(0, 5)

    capacity = random.choice([4, 6, 8, 10])
    occupants = random.randint(0, capacity)
    rooms.append({
        "room_id": room_id,
        "floor": floor,
        "room_number": rn,
        "capacity": capacity,
        "occupants": occupants,
        "risk_level": risk_level,
        "temperature": round(temp, 1),
        "smoke_level": round(smoke, 1),
        "fire_status": fire_status,
    })

with open(os.path.join(HERE, "rooms.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rooms[0].keys()))
    w.writeheader()
    w.writerows(rooms)

# ---------------- occupants.csv ----------------
occupants = []
occ_counter = 1
for r in rooms:
    n_occ = r["occupants"]
    for _ in range(n_occ):
        is_animal = random.random() < 0.08
        occ_type = "Dog" if is_animal else "Human"
        name = "Rescue Dog" if is_animal else f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age_group = random.choice(["Child", "Adult", "Senior"]) if not is_animal else "N/A"

        if r["risk_level"] == "Critical":
            risk_status = random.choice(["Critical", "Critical", "High Risk"])
        elif r["risk_level"] == "High Risk":
            risk_status = random.choice(["High Risk", "High Risk", "Safe"])
        else:
            risk_status = "Safe"

        is_trapped = risk_status == "Critical" and random.random() < 0.6

        occupants.append({
            "occupant_id": f"OCC-{occ_counter:04d}",
            "room_id": r["room_id"],
            "name": name,
            "type": occ_type,
            "age_group": age_group,
            "risk_status": risk_status,
            "is_trapped": is_trapped,
        })
        occ_counter += 1

with open(os.path.join(HERE, "occupants.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(occupants[0].keys()))
    w.writeheader()
    w.writerows(occupants)

# ---------------- incidents.csv ----------------
incidents = []
inc_counter = 1
now = datetime.utcnow()
for r in rooms:
    if r["risk_level"] in ("Critical", "High Risk") or random.random() < 0.15:
        severity = "Critical" if r["risk_level"] == "Critical" else random.choice(["High", "Moderate"])
        incident_type = random.choice(["Fire", "Smoke Detection", "Gas Leak", "Electrical Fault"])
        detected_at = now - timedelta(minutes=random.randint(1, 240))
        occ_count = r["occupants"]
        # crude risk score approximation for the CSV column (backend recalculates via risk engine)
        risk_score = min(100, round(
            (r["temperature"] - 25) * 0.5 + r["smoke_level"] * 0.5 + occ_count * 2, 1))
        risk_score = max(risk_score, 5)

        incidents.append({
            "incident_id": f"INC-{inc_counter:04d}",
            "building_id": BUILDING_ID,
            "floor": r["floor"],
            "room": r["room_id"],
            "incident_type": incident_type,
            "severity": severity,
            "temperature": r["temperature"],
            "smoke_level": r["smoke_level"],
            "fire_status": r["fire_status"],
            "detected_at": detected_at.strftime("%Y-%m-%d %H:%M:%S"),
            "occupants_count": occ_count,
            "risk_score": risk_score,
        })
        inc_counter += 1

with open(os.path.join(HERE, "incidents.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(incidents[0].keys()))
    w.writeheader()
    w.writerows(incidents)

# ---------------- sensor_readings.csv ----------------
sensor_readings = []
reading_counter = 1
for r in rooms:
    for t_offset in range(6):  # 6 historical readings per room
        ts = now - timedelta(minutes=(5 - t_offset) * 15)
        jitter_temp = r["temperature"] + random.uniform(-3, 3)
        jitter_smoke = max(0, r["smoke_level"] + random.uniform(-5, 5))
        co_level = round(random.uniform(0, 20) if r["risk_level"] in ("Safe", "Moderate")
                          else random.uniform(40, 180), 1)
        flame_detected = r["fire_status"] == "active" and t_offset >= 3
        humidity = round(random.uniform(25, 55), 1)

        sensor_readings.append({
            "reading_id": f"RD-{reading_counter:05d}",
            "room_id": r["room_id"],
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": round(jitter_temp, 1),
            "smoke_level": round(jitter_smoke, 1),
            "co_level": co_level,
            "flame_detected": flame_detected,
            "humidity": humidity,
        })
        reading_counter += 1

with open(os.path.join(HERE, "sensor_readings.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(sensor_readings[0].keys()))
    w.writeheader()
    w.writerows(sensor_readings)

# ---------------- rescue_teams.csv ----------------
team_names = ["Rescue Team A", "Rescue Team B", "Rescue Team C", "Rescue Team D", "Hazmat Unit"]
critical_rooms = [r["room_id"] for r in rooms if r["risk_level"] in ("Critical", "High Risk")]
rescue_teams = []
for i, name in enumerate(team_names):
    if i < len(critical_rooms):
        status = random.choice(["En Route", "On Scene"])
        assigned_room = critical_rooms[i]
        eta = round(random.uniform(1, 8), 1) if status == "En Route" else 0
    else:
        status = "Standby"
        assigned_room = ""
        eta = 0
    rescue_teams.append({
        "team_id": f"TEAM-{i+1:02d}",
        "team_name": name,
        "status": status,
        "current_location": random.choice(["Lobby", "Stair A", "Stair B", "Parking Bay", "Command Truck"]),
        "assigned_room": assigned_room,
        "eta_minutes": eta,
    })

with open(os.path.join(HERE, "rescue_teams.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rescue_teams[0].keys()))
    w.writeheader()
    w.writerows(rescue_teams)

print("Datasets generated:")
print(f"  rooms.csv            -> {len(rooms)} rows")
print(f"  occupants.csv        -> {len(occupants)} rows")
print(f"  incidents.csv        -> {len(incidents)} rows")
print(f"  sensor_readings.csv  -> {len(sensor_readings)} rows")
print(f"  rescue_teams.csv     -> {len(rescue_teams)} rows")
