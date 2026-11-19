# RESQ AI — Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination

**Detect • Locate • Rescue • Save Lives**

A full-stack **prototype** of a fire-safety command center: React dashboard → FastAPI backend → SQLite.
It runs locally on **simulated** building and sensor data. It is a demonstration, not a certified life-safety system.

## 1. What it does

- Shows a 4-floor, 24-room building with live room status (temperature, smoke, fire, occupancy, sensor health).
- Scores every reading with a transparent **rule-based risk engine** (0–100) and explains the score factor by factor.
- Opens an incident automatically when a room's score goes above 60, and walks it through a lifecycle:
  Detected → Acknowledged → Assigned → En Route → On Scene → Resolved (each step timestamped).
- Plans **evacuation and rescue routes** over a building graph (rooms, corridors, stairs, exits), avoiding blocked exits and hazards.
- Dispatches rescue teams, tracks arrival, marks people rescued, and measures real response time.
- Raises **notifications and escalations** if an incident is not acknowledged in time.
- Shows an experimental **ML forecast** ("may reach High Risk in the next 10 minutes") separately from the observed risk.
- Role-based login (viewer / operator / admin) and an audit log of every action.

## 2. Honest limits (read this before presenting)

- **All data is simulated.** No real sensors, cameras, GPS or people. Camera tiles are labelled *SIMULATED*.
- The **risk engine is rule-based**, not machine learning. The weights are expert-style heuristics, not learned.
- The **ML forecast is trained on synthetic episodes** produced by this project's own simulator. Its test results show the pipeline works; they are **not** field accuracy. Sudden fires (little warning in the data) are the main misses.
- Demo passwords, `RESQ_SECRET_KEY` and `RESQ_DEVICE_KEY` defaults are public in this repo. Change them for anything beyond a local demo.
- SQLite and a single process suit one building. Docker files are provided but were not tested in the build environment.
- Not implemented: CCTV video analytics, rescue-team GPS, SMS/e-mail/push notifications (plans in `docs/INTEGRATION.md`).

## 3. Architecture

```
RESQ_AI/
├── frontend/   React 18 + Vite dashboard (talks to the backend only through REST)
├── backend/    FastAPI app: routers, services, models, ML, tests
├── database/   SQLite file (resqai.db, created by seed_database.py)
├── docs/       INTEGRATION.md (sensor API, CSV, cameras, notifications, backup, deployment)
└── docker-compose.yml
```

**Frontend:** React 18, Vite, Recharts, Axios, lucide-react, three.js (@react-three/fiber, drei) for the 3D building.
**Backend:** Python 3, FastAPI, SQLAlchemy 2, Pydantic v2, Uvicorn. Auth uses only the standard library (HMAC-signed tokens, PBKDF2 password hashes).
**Database:** 16 tables — Building, Floor, Room, Occupant, Incident, SensorReading, RescueTeam, MedicalSupport, IncidentTimeline, CameraFeed, TopologyNode, TopologyEdge, User, AuditLog, MLPrediction, Notification.

## 4. Risk engine (`backend/app/services/risk_engine.py`)

| Factor | Max points |
|---|---|
| Temperature | 25 |
| Smoke | 25 |
| Carbon monoxide | 15 |
| Fire status | 20 |
| Occupancy | 10 |
| Blocked exit | 5 |

Bands: **Safe** ≤ 30, **Moderate** ≤ 60, **High Risk** ≤ 80, **Critical** > 80. Incident severity always follows the band.

**Emergency overrides** only ever *raise* the score to a minimum: flame + active fire → Critical; CO ≥ 200 ppm → Critical; active fire, flame, or ≥ 120 °C → at least High Risk.
Each result includes `score_breakdown` (points per factor), `weighted_score` (before overrides), `overrides_applied` and `contributing_factors`. A sensor that sent nothing adds 0 points and is flagged (`data_quality: partial`), never treated as "safe".

## 5. ML forecast (`backend/ml/`, see `ml/README.md`)

Target: *will the room's risk score exceed 60 within the next 10 minutes?* Gradient-boosted trees in pure Python, trained on simulated episodes split **by episode** (train/validation/test). Threshold chosen on validation to favour recall (a missed fire costs more than a false alarm). `python -m ml.train` regenerates `model.json` (versioned, checksummed) and `report.json` (confusion matrix, false alarms, missed detections, calibration, Brier score, per-scenario results, comparison with logistic regression and "current score" baselines).
Every logged prediction stores its `model_version`.

## 6. Running it

Requirements: Python 3.10+ and Node.js 18+.

```bash
# Terminal 1 — backend
cd backend
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python seed_database.py
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. API docs: **http://localhost:8000/docs**.
Demo accounts: `admin / admin123` (everything, reset, audit log), `operator / operator123` (run incidents), `viewer / viewer123` (read-only).
If you update the code and see "no such column", delete `database/resqai.db` and run `python seed_database.py` again.

Demo flow: sign in as operator → **Simulate Fire** → acknowledge the incident → dispatch a rescue team → team arrives → complete rescue. Admin can **Reset** the demo.

## 7. Main API endpoints (full list at `/docs`)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/audit-logs` (admin) |
| Building | `GET /api/dashboard/summary`, `/api/floors`, `/api/rooms`, `/api/occupants` |
| Incidents | `GET /api/incidents`, `/active`, `/{id}`; `POST /{id}/acknowledge`, `/{id}/resolve` |
| Rescue | `GET /api/rescue-teams`; `POST /{id}/dispatch`, `/arrive`, `/complete-rescue`, `/navigate` |
| Routing | `GET /api/topology`, `/api/exits`, `/api/routes/evacuation/{room}`, `/api/routes/rescue/{room}`; `POST /api/topology/nodes/{id}/block` |
| Sensors | `POST /api/sensors/ingest` (batch), `/api/sensors/import-csv`, `/api/rooms/{id}/sensor-reading` (the batch and CSV endpoints accept an operator login or `X-Device-Key`) |
| Cameras | `GET /api/cameras`, `POST /api/cameras/{id}/status` (device status and stream status are separate) |
| Live / alerts | `GET /api/live/version`, `GET /api/notifications`, `POST /api/notifications/read` |
| ML | `GET /api/ml/model-info`, `/api/ml/forecast`, `/api/ml/predictions`; `POST /api/ml/predict/{room}` |
| Demo | `POST /api/simulation/fire` (operator), `POST /api/simulation/reset` (admin), `POST /api/risk/calculate` |

## 8. Tests and checks

```bash
cd backend
python -m unittest discover -s tests -t .     # 70+ tests: risk engine, ML, API, end-to-end fire flow,
                                              # multi-incident, blocked exits, restart and backup/restore
python crosscheck.py --simulate               # dashboard numbers vs database consistency checks
cd ../frontend && npm run build               # production build
```

Tests use a temporary database, so they never touch `database/resqai.db`.

## 9. Operations

- Backup / restore: `python backup_db.py backup | list | verify FILE | restore FILE` (see `docs/INTEGRATION.md`).
- Configuration: `backend/.env.example` (secrets, escalation time, stale-sensor threshold, database path).
- Live updates use a 5-second poll of `/api/live/version` (no WebSocket dependency).

## 10. Folder structure

```
backend/
  app/{main.py, config.py, database/, models/, schemas/,
       routers/ (core, incidents, response, analytics, simulation, auth, topology, sensors, live, ml),
       services/ (risk_engine, ingest, lifecycle, topology, notifications, auth, audit, validation, ml_forecast, live)}
  ml/                 data generator, trainer, model.json, report.json
  tests/              unittest suites
  dataset/            CSVs + generate_datasets.py
  seed_database.py, crosscheck.py, backup_db.py, requirements.txt, .env.example, Dockerfile
frontend/src/{api/, components/, pages/}
```

## 11. Future scope

- Real IoT sensors and cameras (MQTT, Raspberry Pi) feeding the existing sensor API; ML/YOLO fire detection on camera streams.
- Train the forecast on real sensor history; re-check calibration per building.
- Push alerts (SMS / e-mail / app), rescue-team GPS, WebSocket live updates.
- PostgreSQL and multi-building support for real deployments.
