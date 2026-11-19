from tests.api_base import ApiCase, TestClient, app, DEVICE, wipe_and_seed, login
from app.services.risk_engine import level_from_score, severity_from_risk_level


class EndToEndFire(ApiCase):
    def test_simulate_to_rescue_full_lifecycle(self):
        op = self.operator
        rescued = lambda: sum(1 for o in op.get("/api/occupants").json() if o.get("is_rescued"))
        before = rescued()
        inc = self.simulate()
        self.assertEqual(inc["lifecycle"], "Detected")
        self.assertEqual(inc["status"], "active")
        # risk score, level and severity can never contradict each other
        self.assertEqual(inc["risk_level"], level_from_score(inc["risk_score"]))
        self.assertEqual(inc["severity"], severity_from_risk_level(inc["risk_level"]))

        iid, room = inc["incident_id"], inc["room_id"]
        self.assertEqual(op.post(f"/api/incidents/{iid}/acknowledge").json()["lifecycle"], "Acknowledged")

        team = self.standby_teams()[0]
        t = op.post(f"/api/rescue-teams/{team}/dispatch", params={"incident_id": iid}).json()
        self.assertEqual((t["status"], t["assigned_room"]), ("En Route", room))
        self.assertEqual(op.get(f"/api/incidents/{iid}").json()["lifecycle"], "En Route")

        self.assertEqual(op.post(f"/api/rescue-teams/{team}/arrive").json()["status"], "On Scene")
        self.assertEqual(op.get(f"/api/incidents/{iid}").json()["lifecycle"], "On Scene")

        done = op.post(f"/api/rescue-teams/{team}/complete-rescue")
        self.assertEqual(done.status_code, 200, done.text)
        final = op.get(f"/api/incidents/{iid}").json()
        self.assertEqual((final["status"], final["lifecycle"]), ("resolved", "Resolved"))
        for k in ("acknowledged_at", "dispatched_at", "en_route_at", "on_scene_at", "resolved_at"):
            self.assertIsNotNone(final[k], k)

        self.assertGreater(rescued(), before)          # People Rescued comes from real rescue status
        self.assertEqual([o for o in op.get("/api/occupants").json() if o["room_id"] == room and o.get("is_trapped") and o.get("is_rescued")], [])

        events = " ".join(e["event"] for e in op.get("/api/timeline").json() if e["incident_id"] == iid)
        self.assertIn("en route", events.lower())
        actions = [a["action"] for a in self.admin.get("/api/audit-logs").json()]
        for a in ("simulate_fire", "dispatch_team", "team_arrived"):
            self.assertIn(a, actions)

    def test_invalid_references_are_clean_errors(self):
        op = self.operator
        self.assertEqual(op.post("/api/incidents/NOPE/acknowledge").status_code, 404)
        self.assertEqual(op.get("/api/incidents/NOPE").status_code, 404)
        self.assertEqual(op.post("/api/rescue-teams/NOPE/dispatch").status_code, 404)
        self.assertEqual(op.get("/api/rooms/NOPE").status_code, 404)
        self.assertEqual(op.get("/api/routes/evacuation/NOPE").status_code, 404)
        self.assertEqual(op.post("/api/ml/predict/NOPE").status_code, 404)

    def test_cannot_dispatch_busy_team_or_resolved_incident(self):
        op = self.operator
        inc = self.simulate()
        team = self.standby_teams()[0]
        self.assertEqual(op.post(f"/api/rescue-teams/{team}/dispatch", params={"incident_id": inc["incident_id"]}).status_code, 200)
        self.assertEqual(op.post(f"/api/rescue-teams/{team}/dispatch", params={"incident_id": inc["incident_id"]}).status_code, 409)
        op.post(f"/api/rescue-teams/{team}/arrive")
        op.post(f"/api/rescue-teams/{team}/complete-rescue")
        other = self.standby_teams()[0]
        self.assertEqual(op.post(f"/api/rescue-teams/{other}/dispatch", params={"incident_id": inc["incident_id"]}).status_code, 409)

    def test_arrive_requires_en_route(self):
        team = self.standby_teams()[0]
        self.assertEqual(self.operator.post(f"/api/rescue-teams/{team}/arrive").status_code, 409)


class MultiIncident(ApiCase):
    def test_several_fires_are_independent_and_prioritised(self):
        op = self.operator
        ids = {self.simulate()["incident_id"] for _ in range(3)}
        self.assertEqual(len(ids), 3)                                   # unique ids, no collisions
        active = op.get("/api/incidents/active").json()
        scores = [i["risk_score"] for i in active]
        self.assertEqual(scores, sorted(scores, reverse=True))          # worst first
        self.assertTrue(ids <= {i["incident_id"] for i in active})

    def test_default_dispatch_goes_to_highest_risk_unassigned(self):
        op = self.operator
        for _ in range(2):
            self.simulate()
        waiting = [i for i in op.get("/api/incidents/active").json() if not i["assigned_team_id"]]
        top = max(waiting, key=lambda i: i["risk_score"])
        team = self.standby_teams()[0]
        t = op.post(f"/api/rescue-teams/{team}/dispatch").json()
        self.assertEqual(t["assigned_room"], top["room_id"])

    def test_two_teams_two_incidents_no_double_assignment(self):
        wipe_and_seed()                      # known state: the seed data has several standby teams
        op = self.operator
        a, b = self.simulate(), self.simulate()
        teams = self.standby_teams()
        self.assertGreaterEqual(len(teams), 2)
        op.post(f"/api/rescue-teams/{teams[0]}/dispatch", params={"incident_id": a["incident_id"]})
        op.post(f"/api/rescue-teams/{teams[1]}/dispatch", params={"incident_id": b["incident_id"]})
        self.assertEqual(op.post(f"/api/rescue-teams/{teams[1]}/dispatch", params={"incident_id": a["incident_id"]}).status_code, 409)
        rooms = {t["assigned_room"] for t in op.get("/api/rescue-teams").json() if t["team_id"] in teams[:2]}
        self.assertEqual(rooms, {a["room_id"], b["room_id"]} if a["room_id"] != b["room_id"] else {a["room_id"]})


class BlockedExits(ApiCase):
    def setUp(self):
        for n in ("X:A", "X:B", "S:A:2", "S:B:2"):
            self.operator.post(f"/api/topology/nodes/{n}/block", json={"blocked": False})

    def route(self, room="2B-203"):
        r = self.operator.get(f"/api/routes/evacuation/{room}").json()
        r["ids"] = [p["node_id"] for p in r.get("path", [])]
        return r

    def test_open_building_has_route_to_an_exit(self):
        r = self.route()
        self.assertTrue(r["found"])
        self.assertTrue(r["ids"][-1].startswith("X:"))

    def test_blocking_nearest_exit_reroutes_to_the_other(self):
        first = self.route()["ids"][-1]
        self.operator.post(f"/api/topology/nodes/{first}/block", json={"blocked": True, "reason": "test"})
        r = self.route()
        self.assertTrue(r["found"])
        self.assertNotEqual(r["ids"][-1], first)
        self.assertNotIn(first, r["ids"])
        self.assertTrue(r["blocked_exits"])

    def test_all_exits_blocked_gives_no_route_and_a_warning(self):
        for n in ("X:A", "X:B"):
            self.operator.post(f"/api/topology/nodes/{n}/block", json={"blocked": True})
        r = self.route()
        self.assertFalse(r["found"])
        self.assertIn("No open exit", r["reason"])
        self.assertEqual(len(r["blocked_exits"]), 2)

    def test_unblocking_restores_route(self):
        for n in ("X:A", "X:B"):
            self.operator.post(f"/api/topology/nodes/{n}/block", json={"blocked": True})
        for n in ("X:A", "X:B"):
            self.operator.post(f"/api/topology/nodes/{n}/block", json={"blocked": False})
        self.assertTrue(self.route()["found"])

    def test_cannot_block_a_room_or_unknown_node(self):
        self.assertEqual(self.operator.post("/api/topology/nodes/R:2B-203/block", json={"blocked": True}).status_code, 400)
        self.assertEqual(self.operator.post("/api/topology/nodes/NOPE/block", json={"blocked": True}).status_code, 404)

    def test_rescue_route_reaches_the_room(self):
        r = self.operator.get("/api/routes/rescue/2B-203").json()
        self.assertTrue(r["found"])
        self.assertEqual(r["path"][-1]["node_id"], "R:2B-203")


class SensorPipeline(ApiCase):
    def test_batch_partial_failure(self):
        r = self.operator.post("/api/sensors/ingest", json={"readings": [
            {"room_id": "1A-101", "temperature": 24, "smoke_level": 2},
            {"room_id": "NOPE", "temperature": 24, "smoke_level": 2},
            {"room_id": "1A-102", "temperature": None, "smoke_level": 5}]}).json()
        self.assertEqual((r["accepted"], r["rejected"]), (2, 1))
        self.assertEqual(self.operator.get("/api/rooms/1A-102").json()["sensor_status"], "missing")

    def test_out_of_range_value_is_422(self):
        r = self.operator.post("/api/sensors/ingest", json={"readings": [{"room_id": "1A-101", "temperature": 9999, "smoke_level": 2}]})
        self.assertEqual(r.status_code, 422)

    def test_fire_reading_opens_exactly_one_incident(self):
        body = {"readings": [{"room_id": "4B-202", "temperature": 140, "smoke_level": 95, "co_level": 190, "flame_detected": True}]}
        a = self.operator.post("/api/sensors/ingest", json=body).json()["results"][0]
        b = self.operator.post("/api/sensors/ingest", json=body).json()["results"][0]
        self.assertTrue(a["incident_opened"])
        self.assertFalse(b["incident_opened"])
        self.assertEqual(a["incident_id"], b["incident_id"])
        self.assertEqual(self.operator.get("/api/rooms/4B-202").json()["risk_level"], "Critical")
        kinds = [n["kind"] for n in self.operator.get("/api/notifications").json()["items"]]
        self.assertIn("new_incident", kinds)

    def test_csv_import_and_bad_header(self):
        csv_body = "room_id,temperature,smoke_level,co_level,flame_detected\n3A-101,25,3,0,false\nBAD,1,1,1,0\n3A-102,,9,,\n"
        r = self.operator.post("/api/sensors/import-csv", content=csv_body, headers={"Content-Type": "text/csv"}).json()
        self.assertEqual((r["accepted"], r["rejected"]), (2, 1))
        self.assertEqual(self.operator.post("/api/sensors/import-csv", content="a,b\n1,2\n").status_code, 422)

    def test_live_version_changes_after_a_write(self):
        v1 = self.operator.get("/api/live/version").json()["version"]
        self.operator.post("/api/sensors/ingest", json={"readings": [{"room_id": "1A-101", "temperature": 23, "smoke_level": 1}]})
        self.assertGreater(self.operator.get("/api/live/version").json()["version"], v1)

    def test_camera_status_is_separate_for_device_and_stream(self):
        r = TestClient(app).post("/api/cameras/CAM-1A-101/status", headers=DEVICE,
                                 json={"device_status": "online", "stream_status": "no_signal"}).json()
        self.assertEqual((r["status"], r["stream_status"]), ("online", "no_signal"))
        self.assertEqual(self.viewer.post("/api/cameras/CAM-1A-101/status", json={"stream_status": "live"}).status_code, 403)


class MachineLearningApi(ApiCase):
    def test_model_info_and_forecast(self):
        info = self.viewer.get("/api/ml/model-info").json()
        self.assertTrue(info["available"])
        self.assertIn("SYNTHETIC", info["trained_on"])
        f = self.viewer.get("/api/ml/forecast").json()["forecasts"]
        self.assertEqual(len(f), 24)
        for x in f:
            if x["available"]:
                self.assertTrue(0 <= x["probability"] <= 1)

    def test_prediction_is_logged_with_model_version(self):
        r = self.operator.post("/api/ml/predict/1A-101").json()
        self.assertTrue(r["available"])
        log = self.operator.get("/api/ml/predictions").json()
        self.assertEqual(log[0]["room_id"], "1A-101")
        self.assertEqual(log[0]["model_version"], r["model_version"])

    def test_stale_sensor_gets_no_forecast(self):
        from datetime import datetime, timedelta
        from app.database.db import SessionLocal
        from app.models import models as m
        db = SessionLocal()
        db.query(m.Room).filter_by(room_id="2A-101").update({"last_sensor_update": datetime.utcnow() - timedelta(days=2)})
        db.commit(); db.close()
        r = self.operator.post("/api/ml/predict/2A-101").json()
        self.assertFalse(r["available"])
        self.assertIn("stale", r["reason"])


class ResetDemo(ApiCase):
    def test_admin_reset_restores_seed_and_keeps_accounts(self):
        for _ in range(2):
            self.simulate()
        n = len(self.admin.get("/api/incidents").json())
        self.assertGreater(n, 5)
        self.assertEqual(self.admin.post("/api/simulation/reset").status_code, 200)
        self.assertEqual(len(self.admin.get("/api/incidents").json()), 5)
        self.assertEqual(login("operator").get("/api/rooms").status_code, 200)   # accounts survived
