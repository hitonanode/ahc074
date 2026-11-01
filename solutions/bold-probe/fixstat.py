"""How handle-hole mismatches of a cmp-* run are fixed.
Per request: raw mismatches (as in holecost2.py) and, for each mismatched hole h_j, how many papers of
column j were moved, and whether the final visible paper at h_j is a column-j paper (dig) or a paper
of another column (filler).
usage: fixstat.py RUN SEED..."""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
reqs = 0; raw = 0; byfill = 0; bydig = 0; digs = Counter(); okmoved = 0; okholes = 0
for seed in map(int, sys.argv[2:]):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    lvl = {}
    for k in range(6, 192):
        # column = deepest opaque handle in chain order; chain order = by number of papers opaque
        pass
    cnt = {j: sum((d[k].opaque >> j) & 1 for k in range(6, 192)) for j in hw}
    chain = sorted(hw, key=lambda j: -cnt[j])
    pos = {j: i for i, j in enumerate(chain)}
    col = {}
    for k in range(6, 192):
        op = [pos[j] for j in hw if (d[k].opaque >> j) & 1]
        col[k] = max(op) if op else -1
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        moved = Counter()
        for k, dd in ops:
            g.move(k, dd, check=False)
            moved[k] += 1
        g.finish(r)
        top = g.order[0]
        target = g.display()
        prev = start[0]
        seq = [top] + [x for x in start if x != top and x != prev]
        covered = 0; black = 0
        for x in seq:
            black |= d[x].black & ~covered
            covered |= d[x].opaque
        vis = {}
        for x, e in g.exposed().items():
            for j in hw:
                if (e >> j) & 1:
                    vis[j] = x
        reqs += 1
        for j in hw:
            if (d[top].opaque >> j) & 1:
                continue
            c = pos[j]
            nm = sum(m for k, m in moved.items() if k != top and col.get(k) == c)
            if ((black ^ target) >> j) & 1:
                raw += 1
                digs[nm] += 1
                if col.get(vis.get(j)) == c:
                    bydig += 1
                else:
                    byfill += 1
            else:
                okholes += 1
                okmoved += nm > 0
print(f"requests {reqs}  raw mismatches/req {raw/reqs:.2f}  fixed showing own column {bydig/reqs:.2f}  showing another column (filler) {byfill/reqs:.2f}")
print("moves of the column's papers per mismatched hole:", {k: round(v / raw, 3) for k, v in sorted(digs.items())})
print(f"matched holes/req {okholes/reqs:.2f}, of which column moved anyway {okmoved/reqs:.2f}")
