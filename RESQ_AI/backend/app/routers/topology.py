"""
RESQ AI - building map (graph), evacuation / rescue routes, blocked exits
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import topology as topo
from app.services.audit import log_action
from app.services.auth import CurrentUser, require_role

router = APIRouter(tags=["Topology & Routes"])


@router.get("/api/topology")
def get_topology(db: Session = Depends(get_db)):
    """All nodes (rooms, corridors, stairs, exits) and connections, with live hazard / blocked status."""
    return topo.topology_status(db)


@router.get("/api/exits")
def get_exits(db: Session = Depends(get_db)):
    return topo.exits_available(db)


@router.get("/api/routes/evacuation/{room_id}")
def evacuation_route(room_id: str, db: Session = Depends(get_db)):
    if not db.query(m.Room).filter(m.Room.room_id == room_id).first():
        raise HTTPException(status_code=404, detail="Room not found")
    return topo.evacuation_route(db, room_id)


@router.get("/api/routes/rescue/{room_id}")
def rescue_route(room_id: str, db: Session = Depends(get_db)):
    if not db.query(m.Room).filter(m.Room.room_id == room_id).first():
        raise HTTPException(status_code=404, detail="Room not found")
    return topo.rescue_route(db, room_id)


@router.post("/api/topology/nodes/{node_id}/block")
def set_node_blocked(node_id: str, payload: s.BlockRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(require_role("operator"))):
    """Operator marks an exit, stairwell or corridor as blocked (or open again)."""
    node = db.query(m.TopologyNode).filter(m.TopologyNode.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Map point not found")
    if node.node_type == "room":
        raise HTTPException(status_code=400, detail="Rooms cannot be blocked here. Only exits, stairs and corridors.")
    node.blocked = payload.blocked
    node.blocked_reason = (payload.reason or "Blocked by operator") if payload.blocked else None
    log_action(db, user, "block_path" if payload.blocked else "unblock_path", target=node.node_id,
               detail=node.blocked_reason if payload.blocked else None)
    db.commit()
    return {"node_id": node.node_id, "label": node.label, "blocked": node.blocked, "blocked_reason": node.blocked_reason}
