"""
RESQ AI - building topology (graph) and route calculation.

The building is a connected graph stored in the database:
    room  --4 m--  corridor segment (West / Mid / East on each floor)
    corridor West  --3 m--  Stair A      corridor East --3 m-- Stair B
    Stair A(f) --6 m-- Stair A(f+1)      Stair B(f) --6 m-- Stair B(f+1)
    Stair A(ground) --5 m-- Exit A       Stair B(ground) --5 m-- Exit B
Routes are found with Dijkstra's shortest-path algorithm, where live hazards (fire,
smoke, operator-blocked exits/stairs) change the cost of walking through a node.
"""
import heapq
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import models as m

# How much more "expensive" it is to walk through a hazardous node
HAZARD_COST = {"evacuate": {"hazard": 6.0, "smoke": 2.5}, "rescue": {"hazard": 3.0, "smoke": 1.5}}
WALK_SPEED_MPS = {"evacuate": 1.2, "rescue": 1.5}

CORRIDOR_SIDES = ["W", "M", "E"]
SIDE_NAME = {"W": "West", "M": "Mid", "E": "East"}


# ------------------------------------------------------------------ build
def build_topology(db: Session) -> None:
    """Creates the graph from the rooms in the database. Safe to run repeatedly."""
    rooms = db.query(m.Room).all()
    floors = sorted({r.floor_number for r in rooms})
    if not floors:
        return

    existing_nodes = {n.node_id for n in db.query(m.TopologyNode.node_id).all()}
    existing_edges = {(e.from_node, e.to_node) for e in db.query(m.TopologyEdge).all()}

    def node(node_id, ntype, floor, label, room_id=None):
        if node_id not in existing_nodes:
            db.add(m.TopologyNode(node_id=node_id, node_type=ntype, floor_number=floor, label=label, room_id=room_id))
            existing_nodes.add(node_id)

    def edge(a, b, length):
        if (a, b) not in existing_edges and (b, a) not in existing_edges:
            db.add(m.TopologyEdge(from_node=a, to_node=b, length_m=length))
            existing_edges.add((a, b))

    for f in floors:
        for side in CORRIDOR_SIDES:
            node(f"C:{f}:{side}", "corridor", f, f"Corridor F{f} {SIDE_NAME[side]}")
        for stair in ("A", "B"):
            node(f"S:{stair}:{f}", "stair", f, f"Stair {stair} (Floor {f})")
    node("X:A", "exit", floors[0], "Exit A (Stair A, ground)")
    node("X:B", "exit", floors[0], "Exit B (Stair B, ground)")
    db.flush()  # nodes must exist before edges reference them

    for f in floors:
        edge(f"C:{f}:W", f"C:{f}:M", 8)
        edge(f"C:{f}:M", f"C:{f}:E", 8)
        edge(f"S:A:{f}", f"C:{f}:W", 3)
        edge(f"S:B:{f}", f"C:{f}:E", 3)
        if f + 1 in floors:
            edge(f"S:A:{f}", f"S:A:{f + 1}", 6)
            edge(f"S:B:{f}", f"S:B:{f + 1}", 6)
    edge("X:A", f"S:A:{floors[0]}", 5)
    edge("X:B", f"S:B:{floors[0]}", 5)

    # rooms: 3 columns x 2 rows per floor, same order the 3D building uses (sorted by room id)
    for f in floors:
        for idx, room in enumerate(sorted((r for r in rooms if r.floor_number == f), key=lambda r: r.room_id)):
            node(f"R:{room.room_id}", "room", f, f"Room {room.room_id}", room.room_id)
    db.flush()
    for f in floors:
        for idx, room in enumerate(sorted((r for r in rooms if r.floor_number == f), key=lambda r: r.room_id)):
            edge(f"R:{room.room_id}", f"C:{f}:{CORRIDOR_SIDES[idx % 3]}", 4)
    db.commit()


# ------------------------------------------------------------------ live hazards
def _load(db: Session):
    nodes = {n.node_id: n for n in db.query(m.TopologyNode).all()}
    adj: Dict[str, List] = defaultdict(list)
    for e in db.query(m.TopologyEdge).all():
        adj[e.from_node].append((e.to_node, e.length_m))
        adj[e.to_node].append((e.from_node, e.length_m))
    return nodes, adj


def compute_hazards(db: Session, nodes=None, adj=None) -> Dict[str, dict]:
    """node_id -> {"level": fire | hazard | smoke, "reason": text} for everything affected right now."""
    if nodes is None:
        nodes, adj = _load(db)
    hazards: Dict[str, dict] = {}
    for room in db.query(m.Room).all():
        rid = f"R:{room.room_id}"
        if rid not in nodes:
            continue
        if room.fire_status == "active":
            hazards[rid] = {"level": "fire", "reason": f"Fire in {room.room_id}"}
            level, reason = "hazard", f"Fire in {room.room_id}"
        elif (room.smoke_level or 0) >= 70 or room.fire_status == "smoke":
            level, reason = "smoke", f"Heavy smoke near {room.room_id}"
        else:
            continue
        for nb, _ in adj.get(rid, []):
            if nodes[nb].node_type == "corridor":
                prev = hazards.get(nb)
                if not prev or (level == "hazard" and prev["level"] != "hazard"):
                    hazards[nb] = {"level": level, "reason": reason}
    # a stairwell opening onto a hazardous corridor is hazardous too
    for nid, h in list(hazards.items()):
        if nodes[nid].node_type != "corridor":
            continue
        for nb, _ in adj.get(nid, []):
            if nodes[nb].node_type == "stair" and nb not in hazards:
                hazards[nb] = {"level": h["level"] if h["level"] != "fire" else "hazard", "reason": h["reason"]}
    return hazards


def _unavailable(node, hazards) -> Optional[str]:
    if node.blocked:
        return node.blocked_reason or "Blocked by operator"
    return None


# ------------------------------------------------------------------ routing
def _dijkstra(nodes, adj, hazards, start, goal, mode):
    mult = HAZARD_COST[mode]
    dist = {start: 0.0}
    meters = {start: 0.0}
    prev: Dict[str, str] = {}
    heap = [(0.0, start)]
    while heap:
        cost, u = heapq.heappop(heap)
        if u == goal:
            break
        if cost > dist.get(u, float("inf")):
            continue
        for v, length in adj.get(u, []):
            nv = nodes[v]
            if _unavailable(nv, hazards):
                continue                                   # operator-blocked: cannot pass
            h = hazards.get(v)
            if h and h["level"] == "fire" and v != goal:
                continue                                   # never walk through a burning room
            factor = 1.0
            if h:
                factor = mult["smoke"] if h["level"] == "smoke" else mult["hazard"]
            new_cost = cost + length * factor
            if new_cost < dist.get(v, float("inf")):
                dist[v] = new_cost
                meters[v] = meters[u] + length
                prev[v] = u
                heapq.heappush(heap, (new_cost, v))
    if goal not in dist:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path, dist[goal], meters[goal]


def _describe(nodes, hazards, path, meters, cost, mode):
    steps = []
    for nid in path:
        n = nodes[nid]
        h = hazards.get(nid)
        steps.append({"node_id": nid, "label": n.label, "type": n.node_type, "floor": n.floor_number,
                      "hazard": h["level"] if h else None})
    hazard_steps = [s for s in steps if s["hazard"] and s["type"] != "room"] or \
                   [s for s in steps[1:-1] if s["hazard"]]
    return {
        "found": True,
        "path": steps,
        "distance_m": round(meters, 1),
        "estimated_seconds": round(meters / WALK_SPEED_MPS[mode]),
        "through_hazard": bool(hazard_steps),
        "warnings": [hazards[s["node_id"]]["reason"] for s in hazard_steps],
    }


def _blocked_exits(nodes):
    return [{"node_id": n.node_id, "label": n.label, "reason": n.blocked_reason or "Blocked"}
            for n in nodes.values() if n.node_type == "exit" and n.blocked]


def evacuation_route(db: Session, room_id: str) -> dict:
    """Safest/shortest way for the people in `room_id` to reach an open exit."""
    nodes, adj = _load(db)
    start = f"R:{room_id}"
    if start not in nodes:
        return {"found": False, "reason": f"Room {room_id} is not part of the building map."}
    hazards = compute_hazards(db, nodes, adj)
    best = None
    for x in [n for n in nodes.values() if n.node_type == "exit" and not n.blocked]:
        res = _dijkstra(nodes, adj, hazards, start, x.node_id, "evacuate")
        if res and (best is None or res[1] < best[1][1]):
            best = (x.node_id, res)
    blocked = _blocked_exits(nodes)
    if not best:
        return {"found": False, "room_id": room_id, "blocked_exits": blocked,
                "reason": "No open exit can be reached from this room right now."}
    exit_id, (path, cost, meters) = best
    out = _describe(nodes, hazards, path, meters, cost, "evacuate")
    out.update({"room_id": room_id, "mode": "evacuation", "exit": nodes[exit_id].label, "blocked_exits": blocked})
    return out


def rescue_route(db: Session, room_id: str) -> dict:
    """Route for a rescue team from the nearest open exit/entrance to `room_id`."""
    nodes, adj = _load(db)
    goal = f"R:{room_id}"
    if goal not in nodes:
        return {"found": False, "reason": f"Room {room_id} is not part of the building map."}
    hazards = compute_hazards(db, nodes, adj)
    best = None
    for x in [n for n in nodes.values() if n.node_type == "exit" and not n.blocked]:
        res = _dijkstra(nodes, adj, hazards, x.node_id, goal, "rescue")
        if res and (best is None or res[1] < best[1][1]):
            best = (x.node_id, res)
    blocked = _blocked_exits(nodes)
    if not best:
        return {"found": False, "room_id": room_id, "blocked_exits": blocked,
                "reason": "No safe access route to this room right now."}
    entrance, (path, cost, meters) = best
    out = _describe(nodes, hazards, path, meters, cost, "rescue")
    out.update({"room_id": room_id, "mode": "rescue", "entrance": nodes[entrance].label, "blocked_exits": blocked})
    return out


# ------------------------------------------------------------------ status helpers
def topology_status(db: Session) -> dict:
    nodes, adj = _load(db)
    hazards = compute_hazards(db, nodes, adj)

    def view(n):
        h = hazards.get(n.node_id)
        reason = _unavailable(n, hazards)
        return {"node_id": n.node_id, "type": n.node_type, "floor": n.floor_number, "label": n.label,
                "room_id": n.room_id, "blocked": bool(n.blocked), "blocked_reason": n.blocked_reason,
                "hazard": h["level"] if h else None, "hazard_reason": h["reason"] if h else None,
                "passable": not reason and not (h and h["level"] == "fire")}
    edges = [{"from": a, "to": b, "length_m": l} for a, lst in adj.items() for b, l in lst if a < b]
    return {"nodes": [view(n) for n in nodes.values()], "edges": edges}


def exits_available(db: Session) -> dict:
    """An exit is available when it is not blocked and the stairwell leading to it is passable."""
    nodes, adj = _load(db)
    hazards = compute_hazards(db, nodes, adj)
    exits = []
    for n in nodes.values():
        if n.node_type != "exit":
            continue
        stair_ok = True
        for nb, _ in adj.get(n.node_id, []):
            sn = nodes[nb]
            if sn.node_type == "stair" and (sn.blocked or hazards.get(nb)):
                stair_ok = False
        exits.append({"node_id": n.node_id, "label": n.label, "available": (not n.blocked) and stair_ok})
    return {"total": len(exits), "available": sum(1 for e in exits if e["available"]), "exits": exits}
