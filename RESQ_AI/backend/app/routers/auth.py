"""
RESQ AI - login, current user and audit log
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import config
from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import auth as auth_svc
from app.services.audit import log_action

router = APIRouter(tags=["Auth"])


@router.post("/api/auth/login", response_model=s.LoginResponse)
def login(payload: s.LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if auth_svc.login_locked(username):
        raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Please wait a minute and try again.")
    user = db.query(m.User).filter(m.User.username == username).first()
    ok = bool(user and user.active and auth_svc.verify_password(payload.password, user.password_hash))
    auth_svc.record_login_result(username, ok)
    if not ok:
        log_action(db, None, "login", target=username, detail="wrong username or password", success=False, commit=True)
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    log_action(db, auth_svc.CurrentUser(user.username, user.role), "login", target=user.username, commit=True)
    return s.LoginResponse(
        access_token=auth_svc.create_token(user.username, user.role),
        username=user.username, role=user.role, full_name=user.full_name,
    )


@router.get("/api/auth/me")
def me(user: auth_svc.CurrentUser = Depends(auth_svc.get_current_user)):
    return {"username": user.username, "role": user.role, "auth_enabled": config.AUTH_ENABLED}


@router.get("/api/audit-logs", response_model=List[s.AuditLogOut])
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str = Query(None),
    db: Session = Depends(get_db),
    _: auth_svc.CurrentUser = Depends(auth_svc.require_role("admin")),
):
    q = db.query(m.AuditLog)
    if action:
        q = q.filter(m.AuditLog.action == action)
    return q.order_by(m.AuditLog.timestamp.desc(), m.AuditLog.id.desc()).offset(offset).limit(limit).all()
