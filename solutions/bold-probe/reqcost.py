"""Moves per request of a cmp-* run by the requested paper's column (opaque handle count) and kind.
usage: reqcost.py RUN SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
agg = defaultdict(lambda: [0, 0, 0])  # count, moves, holes
kind = defaultdict(lambda: [0, 0])
for seed in map(int, sys.argv[2:]):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        o = d[top].opaque
        nh = sum((o >> j) & 1 for j in hw)
        pair = bin(o & gen).count("1") < 36
        b = min(nh // 4, 7)
        agg[b][0] += 1; agg[b][1] += len(ops); agg[b][2] += 28 - nh
        kind[pair][0] += 1; kind[pair][1] += len(ops)
tot = sum(v[0] for v in agg.values())
for b in sorted(agg):
    c, m, h = agg[b]
    print(f"opaque handles {4*b:2d}-{4*b+3:2d}: share {c/tot:.3f} moves {m/c:.2f} holes {h/c:.1f}")
for p in (False, True):
    c, m = kind[p]
    print("pair" if p else "single", f"share {c/tot:.3f} moves {m/c:.2f}")
