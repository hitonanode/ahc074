"""Pair requests: generic differences |Delta_G| and how many of them show the wrong color at the start
(D on top, previous top removed), against the generic moves; generic moves distribution.
usage: genmis.py SEED..."""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, replay
n = 0; dg = 0; mis = 0; gm = 0; dist = Counter()
for seed in map(int, sys.argv[1:]):
    inp, out, d, gmask, chain, col, _ = load(seed)
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        o = d[top].opaque
        if bin(o & gmask).count("1") == 36:
            continue
        tgt = inp.target[inp.requests[r]]
        prev = start[0]
        seq = [top] + [x for x in start if x != top and x != prev]
        cov = 0; blk = 0
        for x in seq:
            blk |= d[x].black & ~cov
            cov |= d[x].opaque
        hol = gmask & ~o
        n += 1; dg += bin(hol).count("1"); mis += bin((blk ^ tgt) & hol).count("1")
        k = sum(1 for kk, _ in ops if kk < 6); gm += k; dist[k] += 1
print(f"pair requests {n}: |dG| {dg/n:.2f}, mismatched at start {mis/n:.2f}, generic moves {gm/n:.2f} -> {gm/max(mis,1):.3f} moves per mismatched window")
print("generic moves distribution:", {k: round(v / n, 3) for k, v in sorted(dist.items())})
