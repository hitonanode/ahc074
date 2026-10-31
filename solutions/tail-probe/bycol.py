"""Roles of the moves by the target's column, single vs pair targets (brk-probe REQ lines).
usage: bycol.py <errdir>"""
import sys
from collections import defaultdict
from pathlib import Path

H = 34
G = 64 - H
rows = []
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
            depth0 = int(a[25])
            rows.append((l, pair.get(dd, False), n, ops, bin(holes).count("1"), rc, depth0))
mean = lambda v: sum(v) / max(1, len(v))
names = ["ret_prev", "ret_old", "relevel", "blocks", "newfill", "digD", "lift", "fix"]
for kind in (False, True):
    print("pair" if kind else "single", "  l  cnt   n  ops  holes  holemv/h  dig-(n-1)/2  " + "  ".join(names))
    for l in range(H):
        v = [x for x in rows if x[0] == l and x[1] == kind]
        if len(v) < 30:
            continue
        hm = mean([x[5][7] + x[5][4] + x[5][1] + x[5][2] for x in v])
        h = mean([x[4] for x in v])
        print(f"  {l:2d} {len(v):5d} {mean([x[2] for x in v]):4.1f} {mean([x[3] for x in v]):5.2f} {h:5.1f} {hm / max(h, 1e-9):.3f}"
              f" {mean([x[5][5] - (x[2] - 1) / 2 for x in v]):+.2f} " + " ".join(f"{mean([x[5][j] for x in v]):5.2f}" for j in range(8)))
