# RESQ AI - integration guide (sensors, cameras, notifications)

All sensor data - simulator, CSV, batch API, a future real gateway - goes through one pipeline
(`backend/app/services/ingest.py`): validate -> store -> score with the risk engine -> open an incident
automatically if the score is above 60 -> notify. There is only one place to change behaviour.

## 1. Authentication
* People: normal login (operator or admin role).
* Devices / gateways: header `X-Device-Key: <RESQ_DEVICE_KEY>` (set in `backend/.env`; the demo value is NOT secret).

## 2. Send readings (batch, max 500)
`POST /api/sensors/ingest`
```json
{"readings":[{"room_id":"2B-203","temperature":71.5,"smoke_level":42,"co_level":30,"humidity":35,"flame_detected":false}]}
```
* `null`/omitted sensor = "that sensor sent nothing": the room shows NO DATA and the score is flagged partial, never treated as safe.
* A bad row (unknown room, out-of-range value) is rejected on its own; the others are still accepted. The response lists `accepted`, `rejected` and per-row errors.
* `flame_detected: true` sets the room fire status to active.

## 3. CSV import
`POST /api/sensors/import-csv` with the raw CSV as the body (`Content-Type: text/csv`), max 5000 rows.
Header row: `room_id,temperature,smoke_level,co_level,humidity,flame_detected` (only the first three are required; empty cell = missing).
```
curl -X POST http://localhost:8000/api/sensors/import-csv -H "X-Device-Key: KEY" -H "Content-Type: text/csv" --data-binary @readings.csv
```

## 4. Live updates
The dashboard polls `GET /api/live/version` every 5 s (a counter that changes on any database commit) and reloads only when it changes. Polling was chosen over WebSocket for the prototype: no extra dependency, works behind any proxy. A WebSocket/SSE push can replace the poll later without touching the endpoints.

## 5. Cameras: device status vs stream status
Each camera has a **device status** (online/offline) and a separate **stream status** (live / no_signal / simulated).
`POST /api/cameras/{camera_id}/status` `{"device_status":"online","stream_status":"live"}` is the heartbeat. A non-simulated camera that has not reported for `RESQ_CAMERA_STALE_MINUTES` is shown offline. Prototype cameras are `simulated` (there is no real video).

## 6. Notifications and escalation
New automatic incidents raise a notification. An active incident still "Detected" (not acknowledged) after `RESQ_ESCALATE_MINUTES` (default 2) is escalated: level 1 duty operator, 2 supervisor (at 2x the time), 3 incident commander / emergency services (at 3x). Escalations are created once per level. Channel today: dashboard bell. SMS/e-mail/push would be added in `services/notifications.notify()`.

## 7. Not built (optional / future)
* **CCTV analytics:** a model (e.g. YOLO-based fire/smoke detection) would run on a separate worker reading the camera streams and call the same `POST /api/sensors/ingest` (flame_detected) plus the camera status endpoint. Needs real cameras and labelled video; not part of this prototype.
* **GPS for rescue teams:** teams currently have a room/location label. A phone/vehicle tracker would post coordinates to a new `rescue_teams` location endpoint; the map would then draw live positions. Not built.

## 8. Backup, recovery, deployment
* `python backup_db.py backup | list | verify FILE | restore FILE` (backend folder; uses SQLite's online backup, keeps the newest 14, restore first saves the current DB). Stop the API before restoring.
* Environment variables: `backend/.env.example`. `RESQ_DB_PATH` moves the database (e.g. a Docker volume).
* `docker-compose.yml` + the two Dockerfiles are provided for deployment (**not tested in the prototype environment**). SQLite suits a single-building demo; a real multi-site deployment should move to PostgreSQL.
