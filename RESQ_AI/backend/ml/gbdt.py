"""Tiny gradient-boosted decision trees (log-loss), pure Python, histogram splits.
Trees are stored as nested dicts in JSON so inference needs no ML library."""
import math
from ml.features import sigmoid


def _bins(X, nb=16):
    d = len(X[0]); cuts = []
    for j in range(d):
        vals = sorted(set(r[j] for r in X))
        if len(vals) <= nb:
            c = [(vals[i] + vals[i + 1]) / 2 for i in range(len(vals) - 1)]
        else:
            c = sorted(set(vals[int(len(vals) * q / nb)] for q in range(1, nb)))
        cuts.append(c)
    return cuts


def _bin_of(v, c):
    lo, hi = 0, len(c)
    while lo < hi:
        mid = (lo + hi) // 2
        if v <= c[mid]: hi = mid
        else: lo = mid + 1
    return lo


def _build(idx, Bx, g, h, cuts, depth, lam, min_leaf):
    G = sum(g[i] for i in idx); H = sum(h[i] for i in idx)
    leaf = {"leaf": -G / (H + lam)}
    if depth == 0 or len(idx) < 2 * min_leaf:
        return leaf
    best = (0.0, None, None); base = G * G / (H + lam)
    for j in range(len(cuts)):
        nb = len(cuts[j]) + 1
        gs = [0.0] * nb; hs = [0.0] * nb; cs = [0] * nb
        for i in idx:
            b = Bx[i][j]; gs[b] += g[i]; hs[b] += h[i]; cs[b] += 1
        gl = hl = 0.0; cl = 0
        for b in range(nb - 1):
            gl += gs[b]; hl += hs[b]; cl += cs[b]
            if cl < min_leaf or len(idx) - cl < min_leaf: continue
            gr, hr = G - gl, H - hl
            gain = gl * gl / (hl + lam) + gr * gr / (hr + lam) - base
            if gain > best[0]: best = (gain, j, b)
    if best[1] is None:
        return leaf
    _, j, b = best
    L = [i for i in idx if Bx[i][j] <= b]; R = [i for i in idx if Bx[i][j] > b]
    return {"f": j, "t": cuts[j][b],
            "l": _build(L, Bx, g, h, cuts, depth - 1, lam, min_leaf),
            "r": _build(R, Bx, g, h, cuts, depth - 1, lam, min_leaf)}


def tree_value(node, x):
    while "leaf" not in node:
        node = node["l"] if x[node["f"]] <= node["t"] else node["r"]
    return node["leaf"]


def fit(X, y, rounds=60, depth=3, lr=0.2, lam=1.0, min_leaf=40):
    cuts = _bins(X); Bx = [[_bin_of(r[j], cuts[j]) for j in range(len(cuts))] for r in X]
    n = len(X); p0 = min(max(sum(y) / n, 1e-4), 1 - 1e-4)
    base = math.log(p0 / (1 - p0)); F = [base] * n; trees = []
    for _ in range(rounds):
        P = [sigmoid(f) for f in F]
        g = [p - t for p, t in zip(P, y)]; h = [max(p * (1 - p), 1e-6) for p in P]
        tr = _build(list(range(n)), Bx, g, h, cuts, depth, lam, min_leaf)
        trees.append(tr)
        for i in range(n): F[i] += lr * tree_value(tr, X[i])
    return {"base": base, "lr": lr, "trees": trees}


def predict_proba(m, x):
    return sigmoid(m["base"] + m["lr"] * sum(tree_value(t, x) for t in m["trees"]))


def importance(m, names):
    """How often each feature is used as a split (simple, honest importance proxy)."""
    cnt = {n: 0 for n in names}
    def walk(nd):
        if "leaf" in nd: return
        cnt[names[nd["f"]]] += 1; walk(nd["l"]); walk(nd["r"])
    for t in m["trees"]: walk(t)
    return cnt
