"""Train + evaluate the baseline forecaster. Run:  python -m ml.train   (from backend/)
Pure Python (no numpy/sklearn needed). Writes ml/model_v1.json and ml/report.json."""
import json, math, os, hashlib, datetime
from ml.data_gen import build_dataset, split
from ml import gbdt
from ml.features import FEATURE_NAMES, HORIZON_MIN, POSITIVE_SCORE, sigmoid

HERE = os.path.dirname(__file__)
MODEL_VERSION = "gbdt-v1"


def flat(eps):
    X, y, s = [], [], []
    for e in eps:
        for x, lab, sc in e["samples"]:
            X.append(x); y.append(lab); s.append(sc)
    return X, y, s


def fit(X, y, epochs=800, lr=0.3, l2=1e-3, seed=3):
    d = len(X[0]); n = len(X)
    mean = [sum(r[j] for r in X) / n for j in range(d)]
    std = [max(math.sqrt(sum((r[j] - mean[j]) ** 2 for r in X) / n), 1e-6) for j in range(d)]
    Z = [[(r[j] - mean[j]) / std[j] for j in range(d)] for r in X]
    w = [0.0] * d; b = 0.0
    for _ in range(epochs):                       # batch gradient descent, log-loss + L2
        gw = [0.0] * d; gb = 0.0
        for z, t in zip(Z, y):
            p = sigmoid(sum(wi * zi for wi, zi in zip(w, z)) + b)
            e = p - t
            for j in range(d): gw[j] += e * z[j]
            gb += e
        for j in range(d): w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return {"mean": mean, "std": std, "weights": w, "bias": b}


def predict_proba(m, x):
    z = sum(wi * (xi - mu) / sd for wi, xi, mu, sd in zip(m["weights"], x, m["mean"], m["std"])) + m["bias"]
    return sigmoid(z)


def confusion(y, pred):
    tp = sum(1 for a, p in zip(y, pred) if a and p); fp = sum(1 for a, p in zip(y, pred) if not a and p)
    fn = sum(1 for a, p in zip(y, pred) if a and not p); tn = sum(1 for a, p in zip(y, pred) if not a and not p)
    return tp, fp, fn, tn


def metrics(y, pred):
    tp, fp, fn, tn = confusion(y, pred)
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp_false_alarms": fp, "fn_missed": fn, "tn": tn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "false_alarm_rate": round(fp / (fp + tn), 3) if fp + tn else 0.0,
            "miss_rate": round(fn / (fn + tp), 3) if fn + tp else 0.0}


def auc(y, p):
    pairs = sorted(zip(p, y)); rank_sum = 0.0; n1 = sum(y); n0 = len(y) - n1
    i = 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]: j += 1
        avg = (i + j + 1) / 2
        rank_sum += avg * sum(lab for _, lab in pairs[i:j]); i = j
    return round((rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0), 3) if n1 and n0 else None


def calibration(y, p, bins=10):
    out = []
    for k in range(bins):
        lo, hi = k / bins, (k + 1) / bins
        idx = [i for i, v in enumerate(p) if lo <= v < hi or (k == bins - 1 and v == 1.0)]
        if idx:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(idx),
                        "mean_predicted": round(sum(p[i] for i in idx) / len(idx), 3),
                        "observed_rate": round(sum(y[i] for i in idx) / len(idx), 3)})
    ece = sum(b["n"] * abs(b["mean_predicted"] - b["observed_rate"]) for b in out) / len(y)
    return out, round(ece, 3)


def pick_threshold(y, p, scores):
    """Pick the threshold that maximises F2 (recall counts 4x precision: a missed fire is worse
    than a false alarm) on VALIDATION rows where the room is not yet High Risk (the real
    forecasting question - rows already > 60 are trivial)."""
    idx = [i for i, s in enumerate(scores) if s <= POSITIVE_SCORE]
    yy = [y[i] for i in idx]; pp = [p[i] for i in idx]
    best, best_f2 = 0.5, -1
    for t in [i / 100 for i in range(5, 96)]:
        m = metrics(yy, [1 if v >= t else 0 for v in pp])
        d = 4 * m["precision"] + m["recall"]
        f2 = 5 * m["precision"] * m["recall"] / d if d else 0
        if f2 > best_f2: best, best_f2 = t, f2
    return best


def main():
    eps = build_dataset()
    tr, va, te = split(eps)
    Xtr, ytr, _ = flat(tr); Xva, yva, sva = flat(va); Xte, yte, ste = flat(te)
    lr_m = fit(Xtr, ytr)                                   # logistic regression = comparison baseline
    lr_pte = [predict_proba(lr_m, x) for x in Xte]
    m = gbdt.fit(Xtr, ytr)                                 # deployed model
    pva = [gbdt.predict_proba(m, x) for x in Xva]; pte = [gbdt.predict_proba(m, x) for x in Xte]
    thr = pick_threshold(yva, pva, sva)
    brier = lambda y, p: round(sum((a - b) ** 2 for a, b in zip(y, p)) / len(y), 4)
    cal, ece = calibration(yte, pte)

    # baselines on the same test rows
    base_now = metrics(yte, [1 if s > POSITIVE_SCORE else 0 for s in ste])        # persistence: "already High"
    base_mod = metrics(yte, [1 if s > 30 else 0 for s in ste])                    # "already Moderate or worse"
    by_kind = {}
    for e in te:
        k = e["kind"]; by_kind.setdefault(k, [[], []])
        for x, lab, _ in e["samples"]:
            by_kind[k][0].append(lab); by_kind[k][1].append(1 if gbdt.predict_proba(m, x) >= thr else 0)
    per_scenario = {k: {"rows": len(v[0]), "positives": sum(v[0]), **{q: metrics(*v)[q] for q in ("fp_false_alarms", "fn_missed", "precision", "recall")}}
                    for k, v in by_kind.items()}

    model = {
        "model_version": MODEL_VERSION, "model_type": "gradient-boosted decision trees (pure python, 60 trees, depth 3)",
        "trained_on": "SYNTHETIC simulated episodes (not real sensor history)",
        "target": f"room risk_score > {POSITIVE_SCORE} (High Risk/Critical) at any point in the next {HORIZON_MIN} minutes",
        "horizon_minutes": HORIZON_MIN, "decision_threshold": thr,
        "features": FEATURE_NAMES, **m,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
    }
    model["checksum"] = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:12]
    json.dump(model, open(os.path.join(HERE, "model.json"), "w"), indent=2)

    report = {
        "model_version": MODEL_VERSION, "checksum": model["checksum"],
        "data": {"episodes": {"train": len(tr), "validation": len(va), "test": len(te)},
                 "rows": {"train": len(ytr), "validation": len(yva), "test": len(yte)},
                 "positive_rate_test": round(sum(yte) / len(yte), 3), "split": "by episode (no leakage between minutes of one episode)"},
        "threshold_chosen_on_validation": thr, "threshold_rule": "max F2 on validation rows not yet High Risk",
        "test": {"at_threshold": metrics(yte, [1 if v >= thr else 0 for v in pte]),
                 "at_0.5": metrics(yte, [1 if v >= .5 else 0 for v in pte]),
                 "auc": auc(yte, pte), "brier": brier(yte, pte),
                 "brier_always_base_rate": brier(yte, [sum(ytr) / len(ytr)] * len(yte)),
                 "calibration_bins": cal, "expected_calibration_error": ece},
        "early_warning_test": {
            "note": "only rows where the room is NOT yet High Risk (current score <= 60): the real forecasting question",
            "rows": sum(1 for s in ste if s <= POSITIVE_SCORE),
            "positives": sum(1 for s, a in zip(ste, yte) if s <= POSITIVE_SCORE and a),
            "at_threshold": metrics([a for s, a in zip(ste, yte) if s <= POSITIVE_SCORE], [1 if v >= thr else 0 for s, v in zip(ste, pte) if s <= POSITIVE_SCORE]),
            "at_0.5": metrics([a for s, a in zip(ste, yte) if s <= POSITIVE_SCORE], [1 if v >= .5 else 0 for s, v in zip(ste, pte) if s <= POSITIVE_SCORE]),
            "rule_engine_alone": "recall 0 by construction (it only reports the current state)"},
        "baselines_test": {"persistence_score_gt_60": base_now, "persistence_score_gt_30": base_mod},
        "per_scenario_test": per_scenario,
        "feature_split_counts": gbdt.importance(m, FEATURE_NAMES),
        "comparison_logistic_regression_test": {"auc": auc(yte, lr_pte), "brier": brier(yte, lr_pte),
            "at_0.5": metrics(yte, [1 if v >= .5 else 0 for v in lr_pte])},
        "caveat": "Synthetic data: results show the pipeline works on simulator dynamics; they are NOT field accuracy.",
    }
    json.dump(report, open(os.path.join(HERE, "report.json"), "w"), indent=2)
    return report


if __name__ == "__main__":
    r = main()
    t = r["test"]
    print("model", r["model_version"], "threshold", r["threshold_chosen_on_validation"])
    print("data", r["data"])
    print("TEST @thr", t["at_threshold"]); print("AUC", t["auc"], "Brier", t["brier"], "(base-rate Brier", t["brier_always_base_rate"], ") ECE", t["expected_calibration_error"])
    print("EARLY WARNING", r["early_warning_test"])
    print("baseline score>60", r["baselines_test"]["persistence_score_gt_60"])
    print("baseline score>30", r["baselines_test"]["persistence_score_gt_30"])
    for k, v in r["per_scenario_test"].items(): print(" ", k, v)
