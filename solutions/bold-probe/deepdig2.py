"""Composition of the same-column papers above a requested deep single (cmp-* run): pairs vs singles,
and whether they sit in the column region (below every paper of shallower columns) or out of it.
usage: deepdig2.py RUN SEED..."""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
n = 0; tot = Counter()
for seed in map(int, sys.argv[2:]):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    cnt_h = {j: sum((d[k].opaque >> j) & 1 for k in range(6, 192)) for j in hw}
    chain = sorted(hw, key=lambda j: -cnt_h[j]); pos = {j: i for i, j in enumerate(chain)}
    col = {}; pair = {}
    for k in range(6, 192):
        op = [pos[j] for j in hw if (d[k].opaque >> j) & 1]
        col[k] = max(op) if op else -1
        pair[k] = bin(d[k].opaque & gen).count("1") < 36
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        nh = sum((d[top].opaque >> j) & 1 for j in hw)
        if pair[top] or nh < 20:
            continue
        c = col[top]; i = start.index(top)
        # column region of c: below the last paper of any column < c
        last_shallow = max((t for t, x in enumerate(start) if x >= 6 and col[x] < c), default=-1)
        n += 1
        for t, x in enumerate(start[:i]):
            if x < 6 or col[x] != c:
                continue
            tot[("in" if t > last_shallow else "out") + (" pair" if pair[x] else " single")] += 1
print(f"deep single requests {n}: " + ", ".join(f"{k} {v/n:.2f}" for k, v in sorted(tot.items())))
