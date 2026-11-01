"""Raw handle-hole mismatches of a cmp-* run, per handle rank.
At the start of each request: take out the previous top paper, put the requested paper D (top at
the end) on top, and compare the display at D's handle holes with the target.
usage: holecost2.py RUN SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
holes = defaultdict(int); mism = defaultdict(int); reqs = 0; moves = 0
for seed in map(int, sys.argv[2:]):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    cnt = {j: sum((d[k].opaque >> j) & 1 for k in range(6, 192)) for j in hw}
    order = sorted(hw, key=lambda j: -cnt[j])
    rank = {j: i for i, j in enumerate(order)}
    g = replay.Game(inp, d)
    a = inp.a if hasattr(inp, "a") else None
    for r, ops in enumerate(out.queries):
        start = list(g.order)
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        moves += len(ops)
        top = g.order[0]
        target = g.display()  # correct at the end (no mistakes)
        prev = start[0]
        seq = [top] + [x for x in start if x != top and x != prev]
        covered = 0; black = 0
        for x in seq:
            black |= d[x].black & ~covered
            covered |= d[x].opaque
        reqs += 1
        for j in hw:
            if not (d[top].opaque >> j) & 1:
                holes[rank[j]] += 1
                if ((black ^ target) >> j) & 1:
                    mism[rank[j]] += 1
print("requests", reqs, "moves/req", round(moves / reqs, 3))
th = tm = 0
for i in range(28):
    th += holes[i]; tm += mism[i]
    print(f"rank {i:2d}: holes/req {holes[i]/reqs:.3f}  raw mismatch/req {mism[i]/reqs:.3f}  rate {mism[i]/max(1,holes[i]):.2f}")
print(f"total holes/req {th/reqs:.2f} raw mismatch/req {tm/reqs:.2f}")
