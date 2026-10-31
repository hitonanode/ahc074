"""Hole moves (fix + new fillers + old filler returns + re-levels + return of the previous paper)
regressed on the triangle holes, the pair holes and a pair indicator (brk-probe REQ lines).
usage: fitpair.py <errdir>"""
import sys
from pathlib import Path
import numpy as np

H = 34
G = 64 - H
X, Y, L = [], [], []
for f in sorted(Path(sys.argv[1]).glob("*.txt")):
    pair = {}
    for line in f.read_text().splitlines():
        a = line.split()
        if a and a[0] == "PAPERS":
            for x in a[1:]:
                k, c, o = map(int, x.split(":"))
                pair[k] = o < G + c + 1
        elif a and a[0] == "REQ":
            r, u, dd, l, n, ops, pre = map(int, a[1:8])
            holes = int(a[8], 16)
            rc = list(map(int, a[13:22]))
            tri = sum(1 for m in range(H) if holes >> m & 1 and m > l)
            ph = sum(1 for m in range(H) if holes >> m & 1 and m < l)
            isp = 1.0 if pair.get(dd, False) else 0.0
            X.append([1, tri, ph, isp])
            Y.append([rc[0] + rc[1] + rc[2] + rc[4] + rc[7], rc[0], rc[1], rc[2], rc[4], rc[7], ops - rc[3] - rc[5] - rc[6]])
            L.append(l)
X = np.array(X, dtype=float)
Y = np.array(Y, dtype=float)
names = ["hole moves", "ret_prev", "ret_old", "relevel", "newfill", "fix", "ops-blocks-dig-lift"]
for j, nm in enumerate(names):
    c, *_ = np.linalg.lstsq(X, Y[:, j], rcond=None)
    print(f"{nm:22s} const {c[0]:+.3f} tri {c[1]:+.3f} pairh {c[2]:+.3f} pair {c[3]:+.3f}")
# Pairs only, by the number of pair holes
P = X[:, 3] == 1
for j in (0,):
    c, *_ = np.linalg.lstsq(X[P][:, :3], Y[P][:, j], rcond=None)
    print(f"pairs only: const {c[0]:+.3f} tri {c[1]:+.3f} pairh {c[2]:+.3f}")
    S = ~P
    c, *_ = np.linalg.lstsq(X[S][:, :2], Y[S][:, j], rcond=None)
    print(f"singles only: const {c[0]:+.3f} tri {c[1]:+.3f}")
