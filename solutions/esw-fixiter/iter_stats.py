"""Per-seed iteration counts of the time-limited design stages in local runs (for the fixed counts).

Usage: python3 iter_stats.py RUN-ID ...   (runs that designed themselves, not --design-from)
Prints, per stage, the mean / harmonic mean over seeds (of the mean over the runs), the value at
seed 0, and the correlation of the per-seed counts between the first two runs (a seed's own speed).
"""
import math
import re
import sys
from pathlib import Path

RUNS = Path("/home/sato/ahc074/runs")
KEYS = ["map_iters", "gopt_steps", "anneal_iters", "climb_iters", "match_iterations", "match_sec",
        "perforation_sec", "map_end_sec", "anneal_end_sec", "climb_end_sec", "match_end_sec",
        "perforation_end_sec", "helper_end_sec", "req_sec", "end_sec"]
pat = re.compile(r"^(\w+) = ([-+0-9.eE]+)$")


def load(run):
    out = {}
    for f in sorted((RUNS / run / "err").glob("*.txt")):
        d = {}
        for line in f.read_text().splitlines():
            m = pat.match(line)
            if m and m.group(1) in KEYS:
                d[m.group(1)] = float(m.group(2))
        out[int(f.stem)] = d
    return out


if __name__ == "__main__":
    runs = [load(r) for r in sys.argv[1:]]
    for k in KEYS:
        per_seed = {}
        for data in runs:
            for s, d in data.items():
                if k in d:
                    per_seed.setdefault(s, []).append(d[k])
        vals = [sum(v) / len(v) for v in per_seed.values()]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        hm = len(vals) / sum(1 / v for v in vals) if all(v > 0 for v in vals) else float("nan")
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        s0 = per_seed.get(0)
        corr = float("nan")
        if len(runs) >= 2:
            common = [s for s in runs[0] if s in runs[1] and k in runs[0][s] and k in runs[1][s]]
            xs = [runs[0][s][k] for s in common]
            ys = [runs[1][s][k] for s in common]
            if len(xs) > 2:
                mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
                cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                vx = sum((x - mx) ** 2 for x in xs)
                vy = sum((y - my) ** 2 for y in ys)
                corr = cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else float("nan")
        print(f"{k:20s} n={len(vals):4d} mean={mean:12.6g} hm={hm:12.6g} sd={sd:10.4g} "
              f"min={min(vals):10.6g} max={max(vals):10.6g} seed0={s0} corr={corr:.3f}")
