"""For pair papers: generic differences |Delta_G|, handle differences inside the opaque region (pair
holes) and triangle holes, by column; and mismatches at the start (top = D, prev removed).
usage: pairholes.py SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, replay
acc = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
for seed in map(int, sys.argv[1:]):
    inp, out, d, gmask, chain, col, _ = load(seed)
    H = len(chain)
    hpos = {j: i for i, j in enumerate(chain)}
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        c = col[top]
        o = d[top].opaque
        pair = bin(o & gmask).count("1") < 36
        tgt = inp.target[inp.requests[r]]
        # display at the start with D on top and prev removed
        prev = start[0]
        seq = [top] + [x for x in start if x != top and x != prev]
        cov = 0; blk = 0
        for x in seq:
            blk |= d[x].black & ~cov
            cov |= d[x].opaque
        mis = (blk ^ tgt)
        ph = [j for j in chain if not (o >> j) & 1 and hpos[j] <= c]
        th = [j for j in chain if not (o >> j) & 1 and hpos[j] > c]
        key = ("P" if pair else "S", min(c // 7, 3))
        cnt[key] += 1
        a = acc[key]
        a["dG"] += 36 - bin(o & gmask).count("1")
        a["ph"] += len(ph); a["th"] += len(th)
        a["ph_mis"] += sum((mis >> j) & 1 for j in ph)
        a["th_mis"] += sum((mis >> j) & 1 for j in th)
        a["moves"] += len(ops)
for key in sorted(cnt):
    n = cnt[key]; a = acc[key]
    print(f"{key[0]} cols {key[1]*7:2d}-{key[1]*7+6:2d} share {n/sum(cnt.values()):.3f} |dG| {a['dG']/n:5.2f} pairholes {a['ph']/n:5.2f} (mis {a['ph_mis']/n:4.2f}) triholes {a['th']/n:5.2f} (mis {a['th_mis']/n:4.2f}) moves {a['moves']/n:5.2f}")
