#!/usr/bin/env python3
"""Statistics of the ablation runs of PR 90 (solutions/abl-*), read from runs/.

    python3 solutions/abl-eject/ablation_stats.py [TIME]     # TIME: run-id prefix, default 20261104-104051

For each run TIME_abl-* against TIME_eject-single-window (the same --compare / --extend group):
  - the mean log score ratio and its standard error over all seeds, and the wins/ties/losses of the
    ablated version (fewer moves = win);
  - the same over the seeds where neither run used a light plan (fast_requests = 0 in stderr: the
    safety net after 1.80 s scaled). Removing a component that takes time also removes light plans,
    so on a loaded machine the all-seed difference understates its value;
  - the mean number of light requests per case of the ablated run;
  - the per-seed sum of the 12 log ratios (the sum of the leave-one-out effects).
It also prints the base's light requests and its loss against an earlier run of the same source
(BASE_REF, few light plans), by the number of light requests of the base.
"""
import json
import math
import pathlib
import re
import subprocess
import sys

TIME = sys.argv[1] if len(sys.argv) > 1 else "20261104-104051"
BASE_REF = "20261104-085037_eject-single-window"
NAMES = ["abl-reset-cost", "abl-head-reset", "abl-head-climb", "abl-rematch", "abl-perforate", "abl-hole40",
         "abl-fill-demand", "abl-stay-cover", "abl-post-two", "abl-post-prune", "abl-post-repair", "abl-eject"]
common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                        capture_output=True, text=True, check=True).stdout.strip()
RUNS = pathlib.Path(common).parent / "runs"
FAST = re.compile(r"^fast_requests = ([0-9]+)$", re.M)


def load(run):
    d = RUNS / run
    score = {c["seed"]: c["score"] for c in json.loads((d / "result.json").read_text())["cases"]}
    fast = {}
    for s in score:
        m = FAST.findall((d / "err" / f"{s:04d}.txt").read_text())
        fast[s] = int(m[-1]) if m else 0
    return score, fast


def mean_se(x):
    m = sum(x) / len(x)
    return 100 * m, 100 * math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1) / len(x))


bs, bf = load(f"{TIME}_eject-single-window")
print(f"base: light plans in {sum(1 for s in bf if bf[s])} cases, {sum(bf.values()) / len(bf):.2f} requests/case")
if (RUNS / BASE_REF).exists():
    rs, rf = load(BASE_REF)
    print(f"{BASE_REF}: light plans in {sum(1 for s in rf if rf[s])} cases, {sum(rf.values()) / len(rf):.2f} requests/case")
    for lo, hi in [(0, 0), (1, 49), (50, 199), (200, 10**9)]:
        x = [math.log(bs[s] / rs[s]) for s in bs if lo <= bf[s] <= hi and rf[s] == 0]
        if len(x) > 1:
            print(f"  base vs {BASE_REF}, base light requests {lo}..{hi}: n = {len(x)}, %+.3f ± %.3f%%" % mean_se(x))
print(f"{'run':16s} {'all seeds':>28s} {'W/D/L':>14s} {'no light plan':>30s} {'light/case':>10s}")
total = {s: 0.0 for s in bs}
for n in NAMES:
    s, f = load(f"{TIME}_{n}")
    x = [math.log(s[k] / bs[k]) for k in bs]
    for k in bs:
        total[k] += math.log(s[k] / bs[k])
    clean = [math.log(s[k] / bs[k]) for k in bs if f[k] == 0 and bf[k] == 0]
    w = sum(1 for k in bs if s[k] < bs[k])
    t = sum(1 for k in bs if s[k] == bs[k])
    m, e = mean_se(x)
    cm, ce = mean_se(clean)
    print(f"{n:16s} n={len(x)} {m:+.3f} ± {e:.3f}% {w:>5d}/{t}/{len(x) - w - t:<5d}"
          f"   n={len(clean)} {cm:+.3f} ± {ce:.3f}%   {sum(f.values()) / len(f):8.2f}")
print("sum of the 12 differences (per seed): %+.3f ± %.3f%%" % mean_se(list(total.values())))
