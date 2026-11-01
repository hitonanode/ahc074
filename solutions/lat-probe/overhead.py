"""Moves per request by role, grouped by kind (pair/single) and the column of D, to price the pair
overhead at equal depth. Roles: lift (D), prev (the top paper at the start), dig (papers of D's column
above D at the start), gen (generic sheets), fix (everything else: handle-hole fixes, fillers and
their returns). Also: whether prev moved, against c_prev < c_D. usage: overhead.py SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, replay
acc = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
pm = defaultdict(lambda: [0, 0])
for seed in map(int, sys.argv[1:]):
    inp, out, d, gmask, chain, col, _ = load(seed)
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        c = col[top]
        pair = bin(d[top].opaque & gmask).count("1") < 36
        above = set(x for x in start[:start.index(top)] if col.get(x) == c)
        key = ("P" if pair else "S", min(c // 4, 6))
        cnt[key] += 1
        a = acc[key]
        prev = start[0]
        for k, dd in ops:
            if k == top: a["lift"] += 1
            elif k == prev: a["prev"] += 1
            elif k < 6: a["gen"] += 1
            elif k in above: a["dig"] += 1
            else: a["fix"] += 1
        a["tot"] += len(ops)
        if prev >= 6 and prev != top:
            cp = col[prev]
            ppair = bin(d[prev].opaque & gmask).count("1") < 36
            kk = ("P" if pair else "S") + (" prev deeper/eq" if cp >= c else " prev shallower")
            pm[kk][0] += 1
            pm[kk][1] += any(k == prev for k, _ in ops)
tot = sum(cnt.values())
print("kind cols   share  lift  prev   dig   gen   fix  total")
for key in sorted(cnt):
    n = cnt[key]; a = acc[key]
    print(f"{key[0]}   {key[1]*4:2d}-{key[1]*4+3:2d}  {n/tot:.3f} " + " ".join(f"{a[x]/n:5.2f}" for x in ("lift", "prev", "dig", "gen", "fix", "tot")))
for kind in "PS":
    keys = [k for k in cnt if k[0] == kind]
    n = sum(cnt[k] for k in keys)
    print(kind, "all", f"{n/tot:.3f}", " ".join(f"{x} {sum(acc[k][x] for k in keys)/n:.2f}" for x in ("lift", "prev", "dig", "gen", "fix", "tot")))
for k, (n, m) in sorted(pm.items()):
    print(f"{k:22s} n {n/tot:.3f}  prev moved {m/n:.3f}")
