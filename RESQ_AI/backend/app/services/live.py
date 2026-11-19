"""Change counter for live updates. Every committed database write bumps `version`; the dashboard
polls GET /api/live/version (tiny, cheap) and reloads data only when it changed."""
from sqlalchemy import event
from sqlalchemy.orm import Session

_state = {"version": 0}


def current() -> int:
    return _state["version"]


@event.listens_for(Session, "after_commit")
def _bump(_session):
    _state["version"] += 1
