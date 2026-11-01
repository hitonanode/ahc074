"""Classify the moves of each request of a cmp-* run, by the requested paper's kind and depth.
Classes: lift (D itself), prev (the previous top paper), dig (a paper of D's column that was above D
at the start), gen (a generic sheet), other (fillers and handle-hole digs).
usage: moveclass.py RUN SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
acc = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
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
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        pair = bin(d[top].opaque & gen).count("1") < 36
        nh = sum((d[top].opaque >> j) & 1 for j in hw)
        key = ("pair" if pair else "single") + (" deep" if nh >= 20 else " mid" if nh >= 12 else " shallow")
        above = set(x for x in start[:start.index(top)] if col.get(x) == col[top])
        cnt[key] += 1
        for k, dd in ops:
            if k == top: c = "lift"
            elif k == start[0]: c = "prev"
            elif k < 6: c = "gen"
            elif k in above: c = "dig"
            else: c = "other"
            acc[key][c] += 1
tot = sum(cnt.values())
for key in sorted(cnt):
    n = cnt[key]
    print(f"{key:15s} share {n/tot:.3f} " + " ".join(f"{c} {acc[key][c]/n:.2f}" for c in ("lift", "prev", "dig", "gen", "other")) + f"  total {sum(acc[key].values())/n:.2f}")
