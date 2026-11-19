from tests.api_base import ApiCase, TestClient, app, DEVICE


class Auth(ApiCase):
    def test_no_token_is_401_everywhere(self):
        c = TestClient(app)
        for path in ("/api/rooms", "/api/incidents", "/api/dashboard/summary", "/api/ml/forecast", "/api/notifications"):
            self.assertEqual(c.get(path).status_code, 401, path)

    def test_health_and_login_are_open(self):
        c = TestClient(app)
        self.assertEqual(c.get("/api/health").status_code, 200)
        self.assertEqual(c.post("/api/auth/login", json={"username": "viewer", "password": "viewer123"}).status_code, 200)

    def test_wrong_password_rejected(self):
        r = TestClient(app).post("/api/auth/login", json={"username": "operator", "password": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_tampered_token_rejected(self):
        c = TestClient(app)
        c.headers["Authorization"] = self.viewer.headers["Authorization"][:-3] + "abc"
        self.assertEqual(c.get("/api/rooms").status_code, 401)

    def test_viewer_can_read_but_not_act(self):
        self.assertEqual(self.viewer.get("/api/rooms").status_code, 200)
        self.assertEqual(self.viewer.post("/api/simulation/fire").status_code, 403)
        self.assertEqual(self.viewer.post("/api/topology/nodes/X:A/block", json={"blocked": True}).status_code, 403)
        self.assertEqual(self.viewer.post("/api/ml/predict/1A-101").status_code, 403)

    def test_operator_cannot_reset_or_read_audit(self):
        self.assertEqual(self.operator.post("/api/simulation/reset").status_code, 403)
        self.assertEqual(self.operator.get("/api/audit-logs").status_code, 403)

    def test_admin_can_read_audit(self):
        self.assertEqual(self.admin.get("/api/audit-logs").status_code, 200)

    def test_sensor_api_needs_device_key_or_operator(self):
        body = {"readings": [{"room_id": "1A-101", "temperature": 22, "smoke_level": 1}]}
        c = TestClient(app)
        self.assertEqual(c.post("/api/sensors/ingest", json=body).status_code, 401)
        self.assertEqual(c.post("/api/sensors/ingest", json=body, headers={"X-Device-Key": "wrong"}).status_code, 401)
        self.assertEqual(c.post("/api/sensors/ingest", json=body, headers=DEVICE).status_code, 200)
        self.assertEqual(self.viewer.post("/api/sensors/ingest", json=body).status_code, 403)
        self.assertEqual(self.operator.post("/api/sensors/ingest", json=body).status_code, 200)

    def test_login_lockout_after_repeated_failures(self):
        c = TestClient(app)
        codes = [c.post("/api/auth/login", json={"username": "lockme", "password": "x"}).status_code for _ in range(7)]
        self.assertIn(429, codes)
