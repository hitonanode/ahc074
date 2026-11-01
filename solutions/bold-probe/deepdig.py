"""For requests of deep single papers in a cmp-* run: same-column papers above D at the start, and
how many of them are in the column region vs. outside (above the generic layer bottom / pool).
usage: deepdig.py RUN SEED..."""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
n = 0; above_tot = 0; moved_tot = 0; colsize = Counter(); posd = Counter()
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
    col = {}
    for k in range(6, 192):
        op = [pos[j] for j in hw if (d[k].opaque >> j) & 1]
        col[k] = max(op) if op else -1
    size = Counter(col.values())
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        moved = Counter(k for k, _ in ops)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        pair = bin(d[top].opaque & gen).count("1") < 36
        nh = sum((d[top].opaque >> j) & 1 for j in hw)
        if pair or nh < 20:
            continue
        c = col[top]
        above = [x for x in start[:start.index(top)] if col.get(x) == c]
        n += 1; above_tot += len(above); moved_tot += sum(moved[x] for x in above)
        colsize[size[c]] += 1; posd[len(above)] += 1
print(f"deep single requests {n}: same-column papers above D {above_tot/n:.2f}, moves of them {moved_tot/n:.2f}")
print("column sizes (by request):", dict(sorted(colsize.items())))
print("papers above D:", dict(sorted(posd.items())))
