"""Per-seed difference of the moves of the requests other than u0, by distance from the last request of
u0, between a paper-u0 run and a reference run (mean +- standard error over seeds).

usage: python3 u0_dist.py RUN_U0 RUN_REF [SEED_END]
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

run_u, run_r = replay.resolve_run(sys.argv[1]), replay.resolve_run(sys.argv[2])
end = int(sys.argv[3]) if len(sys.argv) > 3 else 96
bins = [(1, 1), (2, 5), (6, 20), (21, 100), (101, 10**9), (None, None)]  # None: before the first u0
per = {b: [] for b in bins}
for seed in range(end):
    errp = run_u / "err" / f"{seed:04d}.txt"
    m = re.search(r"^u0 = (\d+)$", errp.read_text(), re.M) if errp.exists() else None
    if not m:
        continue
    u0 = int(m.group(1))
    inp = replay.load_input(seed)
    ou = replay.parse_output(inp, (run_u / "out" / f"{seed:04d}.txt").read_text())
    orf = replay.parse_output(inp, (run_r / "out" / f"{seed:04d}.txt").read_text())
    acc = {b: [0, 0] for b in bins}
    last = None
    for r, a in enumerate(inp.requests):
        if a == u0:
            last = r
            continue
        dist = None if last is None else r - last
        for b in bins:
            if (b[0] is None and dist is None) or (b[0] is not None and dist is not None and b[0] <= dist <= b[1]):
                acc[b][0] += len(ou.queries[r]) - len(orf.queries[r])
                acc[b][1] += 1
    for b in bins:
        if acc[b][1]:
            per[b].append(acc[b][0] / acc[b][1])
for b in bins:
    v = per[b]
    if not v:
        continue
    mu = sum(v) / len(v)
    se = math.sqrt(sum((x - mu) ** 2 for x in v) / (len(v) - 1) / len(v)) if len(v) > 1 else 0
    print(f"dist {str(b):>16s}: seeds {len(v):3d}  diff/request {mu:+.3f} +- {se:.3f}")
