"""Shared setup for API integration tests: an isolated temporary database, seeded, plus helpers.
Importing this module must happen before anything imports app.database.db."""
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="resq_test_")
os.environ["RESQ_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["RESQ_AUTH"] = "on"
os.environ["RESQ_DEVICE_KEY"] = "test-device-key"
os.environ["RESQ_ESCALATE_MINUTES"] = "2"

from fastapi.testclient import TestClient  # noqa: E402
import seed_database  # noqa: E402
from app.database.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

DEVICE = {"X-Device-Key": "test-device-key"}


def wipe_and_seed():
    db = SessionLocal()
    try:
        for t in reversed(Base.metadata.sorted_tables):
            db.execute(t.delete())
        db.commit()
    finally:
        db.close()
    seed_database.seed()


def login(username):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": username, "password": f"{username}123"})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


class ApiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wipe_and_seed()
        cls.admin, cls.operator, cls.viewer = login("admin"), login("operator"), login("viewer")

    def standby_teams(self):
        return [t["team_id"] for t in self.operator.get("/api/rescue-teams").json() if t["status"] == "Standby"]

    def simulate(self):
        r = self.operator.post("/api/simulation/fire")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["incident"]
