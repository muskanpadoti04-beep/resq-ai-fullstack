"""Restart and database-recovery behaviour."""
import os
from tests.api_base import ApiCase, TestClient, app, engine, wipe_and_seed, login
import backup_db


class Req:
    class url:
        path = "/api/test"


class Recovery(ApiCase):
    def setUp(self):
        wipe_and_seed()

    def incidents(self, client=None):
        return len((client or self.operator).get("/api/incidents").json())

    def test_data_survives_a_restart(self):
        self.simulate()
        n = self.incidents()
        engine.dispose()                                  # drop every open connection, like a process restart
        with TestClient(app) as fresh:                    # runs the startup hooks again
            op = login("operator")
            self.assertEqual(self.incidents(op), n)       # nothing re-seeded, nothing lost
            self.assertEqual(fresh.get("/api/health").status_code, 200)

    def test_backup_then_restore_brings_back_old_state(self):
        before = self.incidents()
        path = backup_db.backup()
        self.assertTrue(backup_db.verify(path))
        self.simulate(); self.simulate()
        self.assertEqual(self.incidents(), before + 2)
        engine.dispose()
        backup_db.restore(path)
        engine.dispose()
        self.assertEqual(self.incidents(login("operator")), before)

    def test_restore_saves_the_current_database_first(self):
        path = backup_db.backup()
        engine.dispose()
        backup_db.restore(path)
        saved = [f for f in os.listdir(backup_db.BACKUP_DIR) if f.startswith("resqai_before_restore_")]
        self.assertTrue(saved)

    def test_bad_backup_is_refused_and_database_untouched(self):
        junk = os.path.join(backup_db.BACKUP_DIR, "junk.db")
        os.makedirs(backup_db.BACKUP_DIR, exist_ok=True)
        open(junk, "wb").write(b"this is not a database")
        self.assertFalse(backup_db.verify(junk))
        before = self.incidents()
        with self.assertRaises(SystemExit):
            backup_db.restore(junk)
        engine.dispose()
        self.assertEqual(self.incidents(login("operator")), before)

    def test_old_backups_are_pruned(self):
        old_keep = backup_db.KEEP
        backup_db.KEEP = 2
        try:
            for i in range(4):
                backup_db.backup()
            names = [f for f in os.listdir(backup_db.BACKUP_DIR) if f.startswith("resqai_2")]
            self.assertLessEqual(len(names), 2)
        finally:
            backup_db.KEEP = old_keep

    def test_backend_reports_clean_503_when_database_is_out_of_date(self):
        from sqlalchemy.exc import OperationalError
        from app.main import operational_error_handler
        import asyncio
        resp = asyncio.run(operational_error_handler(Req(), OperationalError("x", {}, Exception("no such column"))))
        self.assertEqual(resp.status_code, 503)
        self.assertIn(b"seed_database.py", resp.body)
