"""
RESQ AI - Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination
Database connection / session setup (SQLAlchemy + SQLite)
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# RESQ_DB_PATH lets a deployment (e.g. Docker volume) keep the database somewhere else
DB_PATH = os.getenv("RESQ_DB_PATH") or os.path.join(BASE_DIR, "database", "resqai.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _):
    """SQLite ignores foreign keys unless asked, so bad references would slip in silently."""
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
