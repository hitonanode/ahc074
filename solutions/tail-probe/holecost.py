"""Cost per handle hole by handle depth m and by the target's column (regression on the brk-probe
REQ lines): hole moves of a request (fix + new fillers + old filler returns + re-levels) regressed on
the indicators of its handle holes (triangle and pair holes separately). usage: holecost.py <errdir>"""
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

H = 34
G = 64 - H
d = Path(sys.argv[1])
X, Y, Yall, meta = [], [], [], []
for f in sorted(d.glob("*.txt")):
    pair = {}
    for line in f.read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "PAPERS":
            for x in a[1:]:
                k, c, o = map(int, x.split(":"))
                pair[k] = o < G + c + 1
        elif a[0] == "REQ":
            r, u, dd, l, n, ops, pre = map(int, a[1:8])
            holes, mism, fixed, want = (int(x, 16) for x in a[8:12])
            bt = int(a[12])
            rc = list(map(int, a[13:22]))
            row = np.zeros(2 * H + 1)
            for m in range(H):
                if holes >> m & 1:
                    row[m if m > l else H + m] = 1
            row[2 * H] = 1
            X.append(row)
            Y.append(rc[7] + rc[4] + rc[1] + rc[2])
            meta.append((l, pair.get(dd, False), bin(holes).count("1"), bin(mism).count("1")))
X = np.array(X)
Y = np.array(Y, dtype=float)
coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
print(f"requests {len(Y)}; intercept {coef[2*H]:.3f}")
print("cost per triangle hole at handle m (m > l):")
print("  " + " ".join(f"{m}:{coef[m]:.2f}" for m in range(1, H)))
print("cost per pair hole at handle m (m < l):")
print("  " + " ".join(f"{m}:{coef[H+m]:.2f}" for m in range(0, H - 1)))
# Residual of a flat model (per hole cost fitted) by column and pair/single
nh = X[:, :2 * H].sum(1)
c1 = (nh @ Y) / (nh @ nh)
print(f"flat fit: {c1:.3f} per hole")
res = defaultdict(list)
for i, (l, p, h, mm) in enumerate(meta):
    res[(l, p)].append((Y[i], nh[i]))
print("by column l: single (count, hole moves, holes, per hole) | pair (count, hole moves, holes, per hole)")
for l in range(H):
    s = []
    for p in (False, True):
        v = res.get((l, p), [])
        if v:
            ym = sum(a for a, _ in v) / len(v)
            hm = sum(b for _, b in v) / len(v)
            s.append(f"{len(v):5d} {ym:5.2f} {hm:5.1f} {ym / max(hm, 1e-9):.3f}")
        else:
            s.append(" " * 23)
    print(f"  l={l:2d} " + " | ".join(s))
# Per hole cost as a function of the number of holes of the request
byh = defaultdict(list)
for i in range(len(Y)):
    byh[int(nh[i])].append(Y[i])
print("by number of holes: " + " ".join(f"{h}:{sum(v)/len(v)/max(h,1):.2f}({len(v)})" for h, v in sorted(byh.items())))
