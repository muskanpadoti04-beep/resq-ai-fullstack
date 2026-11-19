"""Synthetic labelled history generator.

IMPORTANT (honesty): there is no real fire-sensor history for this prototype, so training
data is SIMULATED. Episodes are minute-by-minute sensor traces from documented scenarios.
Labels are computed from the same rule engine used in the app, looking HORIZON_MIN minutes
ahead. A model trained on this learns the simulator's dynamics, not the real world - it
demonstrates the pipeline (target, split, metrics, versioning), not field accuracy.
"""
import random
from app.services.risk_engine import calculate_risk
from ml.features import HORIZON_MIN, POSITIVE_SCORE, TREND_LAG, make_features

SCENARIOS = ["normal", "cooking_steam", "electrical_smolder", "gradual_fire", "sudden_fire", "sensor_glitch"]
# fire_status per scenario is what the building system would report at that moment
LENGTH = 60


def _clip(v, lo, hi):
    return max(lo, min(hi, v))


def gen_episode(kind: str, rng: random.Random) -> list[dict]:
    occ = rng.choice([0, 0, 1, 2, 4, 6])
    blocked = rng.random() < 0.1
    base_t = rng.uniform(20, 28)
    onset = rng.randint(15, 35)          # minute the event begins
    rows = []
    for m in range(LENGTH):
        t = base_t + rng.gauss(0, 0.6)
        s = abs(rng.gauss(2, 1.5))
        c = abs(rng.gauss(2, 1.5))
        flame, fs = False, "none"
        k = m - onset
        if kind == "cooking_steam" and 0 <= k < 12:          # smoke + a bit warm, never a fire
            s += min(k * 6, 55) + rng.gauss(0, 3); t += min(k * 0.8, 9)
        elif kind == "electrical_smolder" and k >= 0:        # slow heat/CO, smoke late, flame late
            t += k * rng.uniform(1.6, 2.4); s += max(0, k - 4) * 5.5; c += k * 4.5
            if k >= 8: fs = "smoke"
            if k >= 14: flame, fs = True, "active"
        elif kind == "gradual_fire" and k >= 0:
            t += k * rng.uniform(3.0, 4.5); s += k * 6; c += k * 7
            if k >= 3: fs = "smoke"
            if k >= 7: flame, fs = True, "active"
        elif kind == "sudden_fire" and k >= 0:               # flashover-like: ramps fast
            t += k * rng.uniform(9, 14); s += k * 20; c += k * 20
            if k >= 1: flame, fs = True, "active"
        elif kind == "sensor_glitch" and 0 <= k < 3:         # single-sensor spike, no real fire
            t += rng.choice([60, 90]); 
        rows.append({"temperature": _clip(t, 5, 400), "smoke": _clip(s, 0, 100),
                     "co": _clip(c, 0, 600), "flame": flame, "fire_status": fs,
                     "occupants": occ, "exit_blocked": blocked})
    return rows


def score_row(r):
    return calculate_risk(r["temperature"], r["smoke"], r["co"], r["flame"], r["fire_status"],
                          r["occupants"], r["exit_blocked"])["risk_score"]


def label_episode(rows):
    """-> list of (features, label, current_score) for every minute that has a full horizon."""
    scores = [score_row(r) for r in rows]
    out = []
    for i in range(len(rows) - HORIZON_MIN):
        past = rows[i - TREND_LAG] if i >= TREND_LAG else None
        y = 1 if any(sc > POSITIVE_SCORE for sc in scores[i + 1: i + 1 + HORIZON_MIN]) else 0
        out.append((make_features(rows[i], past), y, scores[i]))
    return out


def build_dataset(n_per_kind: int = 60, seed: int = 7):
    """Returns list of episodes: {'id','kind','samples':[(x,y,score)]}. Split is done BY EPISODE."""
    rng = random.Random(seed)
    eps = []
    weights = {"normal": 1.3, "cooking_steam": 1.0, "electrical_smolder": 0.8,
               "gradual_fire": 0.8, "sudden_fire": 0.6, "sensor_glitch": 0.7}
    for kind in SCENARIOS:
        for i in range(int(n_per_kind * weights[kind])):
            eps.append({"id": f"{kind}-{i}", "kind": kind, "samples": label_episode(gen_episode(kind, rng))})
    rng.shuffle(eps)
    return eps


def split(eps, seed=11):
    rng = random.Random(seed)
    idx = list(range(len(eps))); rng.shuffle(idx)
    n = len(eps); a, b = int(n * .6), int(n * .8)
    pick = lambda ids: [eps[i] for i in ids]
    return pick(idx[:a]), pick(idx[a:b]), pick(idx[b:])   # train, validation, test
