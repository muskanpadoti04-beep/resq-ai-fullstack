"""Database backup / restore (SQLite). Uses SQLite's online backup API, so it is safe even while
the API is running. Run from the backend folder:

    python backup_db.py backup            -> database/backups/resqai_YYYYmmdd_HHMMSS.db (keeps the newest 14)
    python backup_db.py list
    python backup_db.py verify FILE       -> integrity check of a backup
    python backup_db.py restore FILE      -> restores it (current DB is first saved as resqai_before_restore_*.db)
STOP the backend before 'restore'.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

from app.database.db import DB_PATH

BACKUP_DIR = os.getenv("RESQ_BACKUP_DIR") or os.path.join(os.path.dirname(DB_PATH), "backups")
KEEP = int(os.getenv("RESQ_BACKUP_KEEP", "14"))


def verify(path: str) -> bool:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        return ok and {"rooms", "incidents", "users"} <= tables
    except sqlite3.Error:
        return False


def backup() -> str:
    if not os.path.isfile(DB_PATH):
        raise SystemExit(f"No database at {DB_PATH}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    dest, n = os.path.join(BACKUP_DIR, f"resqai_{stamp}.db"), 1
    while os.path.exists(dest):                    # two backups in the same second must not overwrite each other
        n += 1
        dest = os.path.join(BACKUP_DIR, f"resqai_{stamp}_{n}.db")
    src = sqlite3.connect(DB_PATH); dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    if not verify(dest):
        os.remove(dest)
        raise SystemExit("Backup failed its integrity check and was discarded.")
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("resqai_2"))
    for old in files[:-KEEP]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return dest


def restore(path: str) -> None:
    if not verify(path):
        raise SystemExit("That file is not a valid RESQ AI database backup. Nothing was changed.")
    if os.path.isfile(DB_PATH):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        keep = os.path.join(BACKUP_DIR, f"resqai_before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
        shutil.copy2(DB_PATH, keep)
        print("Current database saved as", keep)
    for ext in ("-wal", "-shm"):
        if os.path.exists(DB_PATH + ext):
            os.remove(DB_PATH + ext)
    shutil.copy2(path, DB_PATH)
    print("Restored", path, "->", DB_PATH)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "backup":
        print("Backup written:", backup())
    elif cmd == "list":
        for f in sorted(os.listdir(BACKUP_DIR)) if os.path.isdir(BACKUP_DIR) else []:
            print(f, f"{os.path.getsize(os.path.join(BACKUP_DIR, f)) // 1024} KB")
    elif cmd == "verify" and len(sys.argv) > 2:
        print("OK" if verify(sys.argv[2]) else "INVALID"); sys.exit(0 if verify(sys.argv[2]) else 1)
    elif cmd == "restore" and len(sys.argv) > 2:
        restore(sys.argv[2])
    else:
        print(__doc__)
