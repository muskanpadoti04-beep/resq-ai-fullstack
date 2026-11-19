#!/usr/bin/env python3
"""
RESQ AI - software sensor simulator.

Behaves like a real sensor gateway: every few seconds it sends one reading per room to
POST /api/sensors/ingest (same door a real device would use, authenticated with X-Device-Key).
Rooms stay normal until a fire scenario starts; then smoke rises first, temperature and CO
follow, flame is confirmed, and a neighbouring room on the same floor catches smoke later.
Detection, risk score, ML forecast and incident creation all happen in the backend.

Only the Python standard library is needed.

Examples (run from the backend/ folder, backend already running):
    python sensor_simulator.py                         # normal readings + one fire after 30 s
    python sensor_simulator.py --fire-after 10 --repeat 120
    python sensor_simulator.py --room 2B-204 --fire-after 5
    python sensor_simulator.py --fire-after 0          # only normal readings (no fire)
    python sensor_simulator.py --dry-run               # print readings, send nothing
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def load_rooms(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    rooms = [{"room_id": r["room_id"], "floor": int(r["floor"]), "occupants": int(r.get("occupants") or 0)}
             for r in rows]
    if not rooms:
        sys.exit(f"No rooms found in {path}")
    return rooms


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def baseline():
    return {
        "temperature": round(random.uniform(22, 28), 1),
        "smoke_level": round(random.uniform(0, 4), 1),
        "co_level": round(random.uniform(0, 5), 1),
        "humidity": round(random.uniform(30, 50), 1),
        "flame_detected": False,
    }


def fire_reading(t, intensity, rise, hold, cool):
    """Reading for a room `t` seconds after its fire started. intensity 1.0 = full fire."""
    base = baseline()
    if t < 0:
        return base
    if t <= rise + hold:
        p = clamp(t / rise, 0.0, 1.0)
        smoke = 4 + 92 * (p ** 1.2)            # smoke leads
        temp = 24 + 120 * (p ** 2.0)           # heat follows
        co = 3 + 190 * (p ** 2.2)
    else:
        q = clamp((t - rise - hold) / cool, 0.0, 1.0)
        smoke = 96 - (96 - 4) * q
        temp = 144 - (144 - 24) * q
        co = 193 - (193 - 3) * q
    smoke = base["smoke_level"] + (smoke - 4) * intensity
    temp = base["temperature"] + (temp - 24) * intensity
    co = base["co_level"] + (co - 3) * intensity
    jitter = lambda v, s: v + random.uniform(-s, s)
    temp, smoke, co = jitter(temp, 1.5), jitter(smoke, 1.5), jitter(co, 3)
    return {
        "temperature": round(clamp(temp, 15, 400), 1),
        "smoke_level": round(clamp(smoke, 0, 100), 1),
        "co_level": round(clamp(co, 0, 600), 1),
        "humidity": round(clamp(random.uniform(18, 38) if t > 0 else base["humidity"], 0, 100), 1),
        "flame_detected": bool(intensity >= 0.9 and temp >= 70 and smoke >= 50),
    }


def post(url, key, readings):
    body = json.dumps({"readings": readings}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-Device-Key": key})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main():
    ap = argparse.ArgumentParser(description="RESQ AI software sensor simulator")
    ap.add_argument("--url", default=os.getenv("RESQ_API", "http://localhost:8000"))
    ap.add_argument("--key", default=os.getenv("RESQ_DEVICE_KEY", "resq-device-demo-key"))
    ap.add_argument("--rooms-csv", default=os.path.join(HERE, "dataset", "rooms.csv"))
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between sensor batches")
    ap.add_argument("--fire-after", type=float, default=30.0, help="start a fire after N seconds (0 = never)")
    ap.add_argument("--repeat", type=float, default=0.0, help="start another fire N seconds after the last one ended (0 = once)")
    ap.add_argument("--room", default=None, help="room_id for the fire (default: random occupied room)")
    ap.add_argument("--rise", type=float, default=40.0, help="seconds for the fire to reach full strength")
    ap.add_argument("--hold", type=float, default=90.0, help="seconds the fire stays at full strength")
    ap.add_argument("--cool", type=float, default=40.0, help="seconds to cool down afterwards")
    ap.add_argument("--no-spread", action="store_true", help="do not let smoke reach a neighbouring room")
    ap.add_argument("--dry-run", action="store_true", help="print readings instead of sending them")
    args = ap.parse_args()

    rooms = load_rooms(args.rooms_csv)
    by_id = {r["room_id"]: r for r in rooms}
    if args.room and args.room not in by_id:
        sys.exit(f"Unknown room {args.room}. Known rooms: {', '.join(sorted(by_id)[:10])} ...")
    url = args.url.rstrip("/") + "/api/sensors/ingest"

    fires = {}                      # room_id -> (start_time, intensity)
    last_fire_end = None
    started_any = False
    t0 = time.time()
    print(f"RESQ sensor simulator -> {url}  ({len(rooms)} rooms, every {args.interval}s). Ctrl+C to stop.")

    def start_fire(now):
        pool = [r for r in rooms if r["occupants"] > 0 and r["room_id"] not in fires] or rooms
        room = by_id[args.room] if args.room else random.choice(pool)
        fires[room["room_id"]] = (now, 1.0)
        msg = f"FIRE scenario started in {room['room_id']}"
        if not args.no_spread:
            same_floor = [r for r in rooms if r["floor"] == room["floor"]]
            i = same_floor.index(room)
            neighbour = same_floor[(i + 1) % len(same_floor)]
            if neighbour["room_id"] != room["room_id"]:
                fires[neighbour["room_id"]] = (now + 0.6 * args.rise, 0.55)
                msg += f" (smoke will spread to {neighbour['room_id']})"
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    try:
        while True:
            now = time.time()
            elapsed = now - t0
            total = args.rise + args.hold + args.cool

            # finished fires
            for rid in [r for r, (st, _) in fires.items() if now - st > total]:
                del fires[rid]
                last_fire_end = now
                print(f"[{time.strftime('%H:%M:%S')}] sensors in {rid} back to normal")

            # scheduling
            if not fires:
                if not started_any and args.fire_after > 0 and elapsed >= args.fire_after:
                    start_fire(now)
                    started_any = True
                elif started_any and args.repeat > 0 and last_fire_end and now - last_fire_end >= args.repeat:
                    start_fire(now)

            readings = []
            for r in rooms:
                rid = r["room_id"]
                if rid in fires:
                    st, intensity = fires[rid]
                    data = fire_reading(now - st, intensity, args.rise, args.hold, args.cool)
                else:
                    data = baseline()
                readings.append({"room_id": rid, **data})

            if args.dry_run:
                hot = [x for x in readings if x["temperature"] > 40 or x["smoke_level"] > 20]
                print(f"[{time.strftime('%H:%M:%S')}] {len(readings)} readings, {len(hot)} abnormal: "
                      + ", ".join(f"{x['room_id']} T={x['temperature']} S={x['smoke_level']} flame={x['flame_detected']}" for x in hot))
            else:
                try:
                    res = post(url, args.key, readings)
                    for a in res.get("results", []):
                        if a.get("incident_opened"):
                            print(f"[{time.strftime('%H:%M:%S')}] backend OPENED incident {a.get('incident_id')}")
                    if res.get("rejected"):
                        print(f"  warning: {res['rejected']} reading(s) rejected: {res.get('errors', [])[:2]}")
                except urllib.error.HTTPError as e:
                    print(f"  backend refused the batch (HTTP {e.code}): {e.read().decode()[:200]}")
                except urllib.error.URLError as e:
                    print(f"  cannot reach backend: {e.reason} (is uvicorn running?)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
