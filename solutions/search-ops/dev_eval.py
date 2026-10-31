#!/usr/bin/env python3
"""Development measurement (not an official evaluation): runs compiled solutions offline on the local
inputs (the requests are read from the same stdin, nothing is checked by the tester) and averages
the `name = value` lines of their stderr. Use scripts/pahcer_run.py for real evaluations.

    dev_eval.py BIN [BIN ...] --seeds 0-48 [--jobs 6] [--env HUB_ANNEAL=2000000]

With several binaries, also prints the per-seed mean difference of `total_moves` against the first.
"""
import argparse
import concurrent.futures
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.:/-]*)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$")


def run(binary, seed, env):
    inp = (ROOT / "tools" / "in" / f"{seed:04d}.txt").read_text()
    e = dict(os.environ)
    e.update(env)
    p = subprocess.run([binary], input=inp, capture_output=True, text=True, env=e)
    stats = {}
    for line in p.stderr.splitlines():
        m = LINE.match(line)
        if m:
            stats[m.group(1)] = float(m.group(2))
    if p.returncode != 0:
        stats["crash"] = 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bins", nargs="+")
    ap.add_argument("--seeds", default="0-48")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--keys", default="")
    a = ap.parse_args()
    s0, s1 = map(int, a.seeds.split("-"))
    env = dict(kv.split("=", 1) for kv in a.env)
    seeds = list(range(s0, s1))
    res = {}
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(run, b, s, env): (b, s) for b in a.bins for s in seeds}
        for f in concurrent.futures.as_completed(futs):
            res[futs[f]] = f.result()
    keys = a.keys.split(",") if a.keys else None
    for b in a.bins:
        print(f"== {b}")
        agg = {}
        for s in seeds:
            for k, v in res[(b, s)].items():
                agg.setdefault(k, []).append(v)
        for k in sorted(agg):
            if keys and k not in keys:
                continue
            vs = agg[k]
            print(f"  {k:28s} {sum(vs) / len(vs):12.4f}  (n={len(vs)})")
    base = a.bins[0]
    for b in a.bins[1:]:
        d = []
        for s in seeds:
            x, y = res[(base, s)].get("total_moves"), res[(b, s)].get("total_moves")
            if x and y:
                d.append(math.log(y / x))
        if d:
            m = sum(d) / len(d)
            sd = math.sqrt(sum((v - m) ** 2 for v in d) / max(1, len(d) - 1) / len(d))
            w = sum(v < 0 for v in d)
            l = sum(v > 0 for v in d)
            print(f"{b} vs {base}: log ratio {100 * m:+.3f} +- {100 * sd:.3f} %  win/draw/lose {w}/{len(d) - w - l}/{l}")


if __name__ == "__main__":
    main()
