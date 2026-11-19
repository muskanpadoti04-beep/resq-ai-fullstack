# RESQ AI - ML forecast (baseline)

**Target:** will a room's rule-engine risk score exceed 60 (High Risk / Critical) at any point in the next **10 minutes**?
**Data:** SIMULATED minute-by-minute episodes (normal, cooking steam, electrical smoulder, gradual fire, sudden fire, sensor glitch). No real fire history exists for this prototype. Labels come from the same rule engine, looking 10 min ahead.
**Split:** by episode (60/20/20 train/validation/test) so minutes of one episode never leak across sets.
**Model:** gradient-boosted decision trees, pure Python (`ml/gbdt.py`), compared against logistic regression and two "current score" baselines. Decision threshold chosen on validation to maximise F2 (a missed fire costs more than a false alarm).
**Retrain:** `python -m ml.train` (from `backend/`) -> writes `model.json` (versioned, checksummed) and `report.json` (confusion matrix, false alarms, missed detections, calibration bins, Brier score, per-scenario results).
**Serve:** `GET /api/ml/model-info`, `GET /api/ml/forecast`, `POST /api/ml/predict/{room}` (logged to `ml_predictions` with model_version).
**Limits:** results describe the simulator, not field accuracy. Sudden fires are the main misses (little warning in the data). The forecast never changes the observed risk score.
