"""Per request of an imp-all run: D's column, column size, number of same-column papers above D at the
start, pair/single, and moves by class. usage: digstat.py SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, replay
acc = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
for seed in map(int, sys.argv[1:]):
    inp, out, d, gmask, chain, col, _ = load(seed)
    H = len(chain)
    size = defaultdict(int)
    for k in range(6, 192):
        size[col[k]] += 1
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        c = col[top]
        pair = bin(d[top].opaque & gmask).count("1") < 36
        above = [x for x in start[:start.index(top)] if col.get(x) == c]
        key = (("P" if pair else "S"), c // 7)
        cnt[key] += 1
        a = acc[key]
        a["size"] += size[c]
        a["above"] += len(above)
        a["above_pairs"] += sum(1 for x in above if bin(d[x].opaque & gmask).count("1") < 36)
        a["moves"] += len(ops)
        a["holes"] += H - 1 - c
tot = sum(cnt.values())
for key in sorted(cnt):
    n = cnt[key]; a = acc[key]
    print(f"{key[0]} cols {key[1]*7:2d}-{key[1]*7+6:2d} share {n/tot:.3f} size {a['size']/n:5.2f} above {a['above']/n:5.2f} (pairs {a['above_pairs']/n:4.2f}) tri-holes {a['holes']/n:5.2f} moves {a['moves']/n:5.2f}")
