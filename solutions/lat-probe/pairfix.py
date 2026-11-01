"""How mismatched holes are fixed, split into pair holes (inside D's opaque handle range) and
triangle holes (deeper handles): the visible paper at the end is of the hole's own column (rotation)
or of another column (filler); and how many papers sit on the column of a mismatched pair hole.
usage: pairfix.py SEED..."""
import sys
from collections import Counter, defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import load, replay
st = defaultdict(Counter)
for seed in map(int, sys.argv[1:]):
    inp, out, d, gmask, chain, col, _ = load(seed)
    hpos = {j: i for i, j in enumerate(chain)}
    size = Counter(col[k] for k in range(6, 192))
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]; c = col[top]; o = d[top].opaque
        tgt = inp.target[inp.requests[r]]
        prev = start[0]
        seq = [top] + [x for x in start if x != top and x != prev]
        cov = 0; blk = 0
        for x in seq:
            blk |= d[x].black & ~cov
            cov |= d[x].opaque
        vis = {}
        for x, e in g.exposed().items():
            for j in chain:
                if (e >> j) & 1:
                    vis[j] = x
        for j in chain:
            if (o >> j) & 1:
                continue
            kind = "pair" if hpos[j] <= c else "tri"
            m = ((blk ^ tgt) >> j) & 1
            st[kind]["holes"] += 1
            if m:
                st[kind]["mis"] += 1
                own = col.get(vis.get(j)) == hpos[j]
                st[kind]["own" if own else "filler"] += 1
                if kind == "pair":
                    st[kind][f"colsize{min(size[hpos[j]], 6)}"] += 1
for kind, s in st.items():
    print(kind, dict(s))
