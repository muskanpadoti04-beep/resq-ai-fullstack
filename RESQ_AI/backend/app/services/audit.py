"""
RESQ AI - audit log helper. Every important operator action is written to the audit_logs table.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import models as m


def log_action(db: Session, user, action: str, target: Optional[str] = None,
               detail: Optional[str] = None, success: bool = True, commit: bool = False):
    """Adds an audit row to the current session (saved together with the action itself).
    `user` is a CurrentUser or None (e.g. failed login)."""
    db.add(m.AuditLog(
        timestamp=datetime.utcnow(),
        username=getattr(user, "username", None) or "anonymous",
        role=getattr(user, "role", None) or "-",
        action=action, target=target, detail=detail, success=success,
    ))
    if commit:
        db.commit()
