"""Compares the design model of audit-mix with the measured moves per request (REQ_PROBE=1 output of
solutions/audit2-probe). usage: analyze.py <dir with err/> [first seed] [end seed]

Per request the probe prints
  REQ r u d l n ops pre holes mism fixed bt rc0..rc8 ret fret pool
(holes / mism / fixed: hex masks over the handle indices; rc: moves by role 0 return of the previous
paper, 1 return of an old filler, 2 re-level, 3 blocks, 4 new filler, 5 digs of D's column, 6 lift,
7 handle fixes, 8 other), and once per case P1M (p_m(1) per handle) and CSIZE (column sizes).
"""
import sys
from collections import defaultdict
from pathlib import Path



class _NP:
    """Minimal stand-in for the numpy calls used here (no numpy on this machine)."""
    @staticmethod
    def array(v, dtype=float):
        if v and isinstance(v[0], (list, tuple)):
            return [[float(x) for x in row] for row in v]
        return [float(x) for x in v]

    @staticmethod
    def zeros(n):
        return [0.0] * n

    @staticmethod
    def lstsq(X, y):
        n, k = len(X), len(X[0])
        A = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] + [sum(X[i][a] * y[i] for i in range(n))] for a in range(k)]
        for c in range(k):
            piv = max(range(c, k), key=lambda r: abs(A[r][c]))
            A[c], A[piv] = A[piv], A[c]
            for r in range(k):
                if r != c and A[c][c] != 0:
                    f = A[r][c] / A[c][c]
                    A[r] = [A[r][j] - f * A[c][j] for j in range(k + 1)]
        return [A[c][k] / A[c][c] for c in range(k)]


np = _NP()


def mean(v):
    return sum(v) / len(v)

d = Path(sys.argv[1]) / "err"
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
H = 34
rows = []  # (seed, r, u, l, n, ops, pre, holes, mism, fixed, bt, rc(9), ret, fret, pool, p1m)
for f in sorted(d.glob("*.txt")):
    seed = int(f.stem)
    if not (lo <= seed < hi):
        continue
    p1m = None
    for line in f.read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "P1M":
            p1m = [float(x) for x in a[1:]]
        elif a[0] == "REQ":
            r, u, dd, l, n, ops, pre = map(int, a[1:8])
            holes, mism, fixed = (int(x, 16) for x in a[8:11])
            bt = int(a[11])
            rc = list(map(int, a[12:21]))
            ret, fret, pool = map(int, a[21:24])
            rows.append((seed, r, u, l, n, ops, pre, holes, mism, fixed, bt, rc, ret, fret, pool, p1m))
print("requests", len(rows), "cases", len({x[0] for x in rows}))


def bits(m):
    return [i for i in range(H) if m >> i & 1]


# Per request features
feat = []
for (seed, r, u, l, n, ops, pre, holes, mism, fixed, bt, rc, ret, fret, pool, p1m) in rows:
    hb = bits(holes)
    tri = sum(1 for m in hb if m > l)
    pair = sum(1 for m in hb if m < l)
    # color of u at hole m is unknown here; the model's expected fix at m given mismatch obs is not
    # needed: model fixes = sum over holes of (1 - p_m(c_u)). We approximate by 2 p (1 - p) (the
    # average over colors); exact per-color value needs A_u (not printed).
    mfix = sum(2 * p1m[m] * (1 - p1m[m]) for m in hb)
    feat.append(dict(seed=seed, r=r, l=l, n=n, ops=ops, pre=pre, tri=tri, pair=pair, nh=len(hb), mism=bin(mism).count("1"),
                     fixed=bin(fixed).count("1"), bt=bt, rc=rc, ret=ret, fret=fret, pool=pool, mfix=mfix, holes=holes,
                     mismm=mism, fixedm=fixed))

ops = np.array([x["ops"] for x in feat], float)
print(f"moves/request {mean(ops):.3f}")
rc = np.array([x["rc"] for x in feat], float)
rcm = [mean([row[j] for row in rc]) for j in range(9)]
rcol = lambda j: [row[j] for row in rc]
names = ["ret_prev", "ret_old", "relevel", "blocks", "newfill", "digD", "lift", "fix", "other"]
print("roles (pre-merge means):", " ".join(f"{nm} {v:.3f}" for nm, v in zip(names, rcm)))
pre = np.array([x["pre"] for x in feat], float)
print(f"merge saved {mean(pre) - mean(ops):.3f}")
nh = np.array([x["nh"] for x in feat], float)
mism = np.array([x["mism"] for x in feat], float)
fixed = np.array([x["fixed"] for x in feat], float)
mfix = np.array([x["mfix"] for x in feat], float)
tri = np.array([x["tri"] for x in feat], float)
pair = np.array([x["pair"] for x in feat], float)
bt = np.array([x["bt"] for x in feat], float)
nn = np.array([x["n"] for x in feat], float)
ll = np.array([x["l"] for x in feat], float)
print(f"holes/request {mean(nh):.3f} (tri {mean(tri):.3f} pair {mean(pair):.3f}); mismatched at start {mean(mism):.3f}; "
      f"model fixes (2p(1-p)) {mean(mfix):.3f}; dug {mean(fixed):.3f}; fix moves {rcm[7]:.3f}")
print(f"digD {rcm[5]:.3f} vs model (n-1)/2 {mean([(x - 1) / 2 for x in nn]):.3f}; blocks moves {rcm[3]:.3f} vs 0.5*touched {0.5 * mean(bt):.3f}")

# Regression: ops ~ 1 + tri + pair + bt + n
X = [[1, a, b, c, e] for a, b, c, e in zip(tri, pair, bt, nn)]
beta = np.lstsq(X, ops)
print("regression ops ~ 1, tri, pair, blocks, n:", " ".join(f"{b:.3f}" for b in beta))
X2 = [[1, a, c, e] for a, c, e in zip(mfix, bt, nn)]
beta2 = np.lstsq(X2, ops)
print("regression ops ~ 1, model_fixes, blocks, n:", " ".join(f"{b:.3f}" for b in beta2))
X3 = [[1, a, c, e] for a, c, e in zip(mism, bt, nn)]
beta3 = np.lstsq(X3, ops)
print("regression ops ~ 1, mismatched_at_start, blocks, n:", " ".join(f"{b:.3f}" for b in beta3))

# Per handle m: among requests with a hole at m, the mismatch rate at start and the dig rate, vs model 2p(1-p)
print("\nper handle m: holes/req  mism_rate  dig_rate  model(2p(1-p))  dig/mism")
agg = defaultdict(lambda: [0, 0, 0, 0.0])
for x in feat:
    p1m = None
for (seed, r, u, l, n, o, pr, holes, mm, fx, b, rcc, ret, fret, pool, p1m) in rows:
    for m in bits(holes):
        a = agg[m]
        a[0] += 1
        a[1] += mm >> m & 1
        a[2] += fx >> m & 1
        a[3] += 2 * p1m[m] * (1 - p1m[m])
nreq = len(rows)
for m in range(H):
    a = agg[m]
    if a[0] == 0:
        continue
    print(f"  m={m:2d} {a[0] / nreq:6.3f} {a[1] / a[0]:8.3f} {a[2] / a[0]:8.3f} {a[3] / a[0]:10.3f} {a[2] / max(1, a[1]):8.3f}")

# Per target column l: actual ops vs model
print("\nper column l: req  ops  model(dig+fixes*1.0+0.5bt+2)  holes  mism  fixmoves  newfill  n")
aggl = defaultdict(lambda: np.zeros(8))
for x in feat:
    a = aggl[x["l"]]
    for i, v in enumerate([1, x["ops"], (x["n"] - 1) / 2 + x["mfix"] + 0.5 * x["bt"] + 2, x["nh"], x["mism"], x["rc"][7], x["rc"][4], x["n"]]):
        a[i] += v
for l in sorted(aggl):
    a = aggl[l]
    print(f"  l={l:2d} {int(a[0]):5d} {a[1] / a[0]:6.2f} {a[2] / a[0]:8.2f} {a[3] / a[0]:8.2f} {a[4] / a[0]:6.2f} {a[5] / a[0]:7.2f} {a[6] / a[0]:7.2f} {a[7] / a[0]:5.1f}")

# Hole position relative to the target's column: fix rate by (m - l) for triangle holes
print("\ntriangle holes by m - l: count mism_rate dig_rate")
aggd = defaultdict(lambda: [0, 0, 0])
for (seed, r, u, l, n, o, pr, holes, mm, fx, b, rcc, ret, fret, pool, p1m) in rows:
    for m in bits(holes):
        if m <= l:
            continue
        a = aggd[min(m - l, 40)]
        a[0] += 1
        a[1] += mm >> m & 1
        a[2] += fx >> m & 1
for k in sorted(aggd):
    a = aggd[k]
    print(f"  {k:2d} {a[0]:6d} {a[1] / a[0]:.3f} {a[2] / a[0]:.3f}")

# Pair holes (m < l): mism / dig rates by m
print("\npair holes (m < l): count mism_rate dig_rate")
aggp = [0, 0, 0]
for (seed, r, u, l, n, o, pr, holes, mm, fx, b, rcc, ret, fret, pool, p1m) in rows:
    for m in bits(holes):
        if m >= l:
            continue
        aggp[0] += 1
        aggp[1] += mm >> m & 1
        aggp[2] += fx >> m & 1
print(f"  {aggp[0]} {aggp[1] / max(1, aggp[0]):.3f} {aggp[2] / max(1, aggp[0]):.3f}")
