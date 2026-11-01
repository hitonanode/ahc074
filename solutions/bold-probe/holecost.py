"""Where the handle-hole fixes of a cmp-* run happen.
For each request: the active paper D (top at the end), its holes on the handle windows, and for each
such hole whether the paper visible there changed during the request (a fix). Reported per handle
rank (rank = how many handle windows a paper of that column covers).
usage: holecost.py RUN SEED..."""
import sys
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay
run = sys.argv[1]
holes = defaultdict(int); fixes = defaultdict(int); reqs = 0
for seed in map(int, sys.argv[2:]):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    # handle rank of a window: number of dedicated papers... use count of papers opaque at it
    cnt = {j: sum((d[k].opaque >> j) & 1 for k in range(6, 192)) for j in hw}
    order = sorted(hw, key=lambda j: -cnt[j])  # shallow handle (opaque in most papers) first
    rank = {j: i for i, j in enumerate(order)}
    g = replay.Game(inp, d)
    for r, ops in enumerate(out.queries):
        before = {}
        for x, e in g.exposed().items():
            for j in hw:
                if (e >> j) & 1:
                    before[j] = x
        for k, dd in ops:
            g.move(k, dd, check=False)
        g.finish(r)
        top = g.order[0]
        after = {}
        for x, e in g.exposed().items():
            for j in hw:
                if (e >> j) & 1:
                    after[j] = x
        reqs += 1
        for j in hw:
            if not (d[top].opaque >> j) & 1:
                holes[rank[j]] += 1
                if before.get(j) != after.get(j):
                    fixes[rank[j]] += 1
print("requests", reqs)
th = tf = 0
for i in range(28):
    th += holes[i]; tf += fixes[i]
    print(f"rank {i:2d}: holes/req {holes[i]/reqs:.3f}  changed/req {fixes[i]/reqs:.3f}  rate {fixes[i]/max(1,holes[i]):.2f}")
print(f"total holes/req {th/reqs:.2f} changed/req {tf/reqs:.2f}")
