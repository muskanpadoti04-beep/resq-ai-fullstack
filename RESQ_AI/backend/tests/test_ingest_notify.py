import os, tempfile, unittest
from datetime import datetime, timedelta

os.environ.setdefault("RESQ_DB_PATH", os.path.join(tempfile.mkdtemp(), "t.db"))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database.db import Base
from app.models import models as m
from app.services.ingest import ingest_reading, IngestError
from app.services.notifications import run_escalation
from app import config


class Base_(unittest.TestCase):
    def setUp(self):
        eng = create_engine("sqlite://")
        event.listen(eng, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(eng)
        self.db = sessionmaker(bind=eng)()
        b = m.Building(building_id="BLD-01", name="B"); self.db.add(b); self.db.flush()
        self.db.commit()
        self.room = m.Room(room_id="R1", floor_number=1, room_number="1", capacity=4, occupants_count=2)
        self.db.add(self.room); self.db.commit()

    def tearDown(self):
        self.db.close()


class Ingest(Base_):
    def test_normal_reading_no_incident(self):
        r = ingest_reading(self.db, self.room, temperature=24, smoke_level=2, co_level=1)
        self.db.commit()
        self.assertEqual(r["risk_level"], "Safe")
        self.assertIsNone(r["incident_id"])
        self.assertEqual(self.db.query(m.Incident).count(), 0)

    def test_fire_opens_one_incident_and_notifies_once(self):
        a = ingest_reading(self.db, self.room, temperature=130, smoke_level=90, co_level=150, flame_detected=True)
        self.db.commit()
        b = ingest_reading(self.db, self.room, temperature=135, smoke_level=95, co_level=160, flame_detected=True)
        self.db.commit()
        self.assertTrue(a["incident_opened"]); self.assertFalse(b["incident_opened"])
        self.assertEqual(a["incident_id"], b["incident_id"])
        self.assertEqual(self.db.query(m.Incident).count(), 1)
        self.assertEqual(self.db.query(m.Notification).filter_by(kind="new_incident").count(), 1)
        self.assertEqual(self.room.fire_status, "active")

    def test_invalid_value_rejected(self):
        with self.assertRaises(IngestError):
            ingest_reading(self.db, self.room, temperature=5000, smoke_level=2, co_level=1)

    def test_missing_sensor_flagged_not_safe_silently(self):
        r = ingest_reading(self.db, self.room, temperature=None, smoke_level=10, co_level=0)
        self.assertEqual(r["data_quality"], "partial")
        self.assertEqual(self.room.sensor_status, "missing")


class Escalation(Base_):
    def _incident(self, minutes_old, lifecycle="Detected", status="active"):
        inc = m.Incident(incident_id="INC-T", building_id="BLD-01", floor=1, room_id="R1", severity="Critical",
                         detected_at=datetime.utcnow() - timedelta(minutes=minutes_old), risk_score=90,
                         risk_level="Critical", status=status, lifecycle=lifecycle)
        self.db.add(inc); self.db.commit()

    def test_no_escalation_before_threshold(self):
        self._incident(minutes_old=config.ESCALATE_MINUTES / 2)
        self.assertEqual(run_escalation(self.db), 0)

    def test_escalates_and_is_idempotent(self):
        self._incident(minutes_old=config.ESCALATE_MINUTES * 1.5)
        self.assertEqual(run_escalation(self.db), 1)
        self.assertEqual(run_escalation(self.db), 0)

    def test_levels_rise_with_time_capped_at_3(self):
        self._incident(minutes_old=config.ESCALATE_MINUTES * 10)
        self.assertEqual(run_escalation(self.db), 3)
        levels = sorted(n.escalation_level for n in self.db.query(m.Notification).all())
        self.assertEqual(levels, [1, 2, 3])

    def test_acknowledged_or_resolved_not_escalated(self):
        self._incident(minutes_old=config.ESCALATE_MINUTES * 5, lifecycle="Acknowledged")
        self.assertEqual(run_escalation(self.db), 0)

    def test_historic_incident_ignored(self):
        self._incident(minutes_old=60 * (config.ESCALATE_MAX_AGE_HOURS + 1))
        self.assertEqual(run_escalation(self.db), 0)


if __name__ == "__main__":
    unittest.main()
