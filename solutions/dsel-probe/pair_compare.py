#!/usr/bin/env python3
"""Paired comparison of two --design-from --orders runs that evaluated different designs (dsel-probe).

Usage: pair_compare.py RUN_A RUN_B [RUN_C ...]   (run-ids; the first is the baseline)

For every seed in all runs: the mean over the common order sequences j of 100 log(score_X / score_A);
prints the mean and standard error over the seeds, wins / ties / losses, and the mean scores. Scores of
0 (WA) are reported and excluded.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")


def load(run):
    cases = json.loads((RUNS / run / "result.json").read_text())["cases"]
    return {c["seed"]: (c.get("order_scores") or [c["score"]]) for c in cases}


def main():
    runs = sys.argv[1:]
    data = [load(r) for r in runs]
    seeds = sorted(set.intersection(*(set(d) for d in data)))
    base = data[0]
    print(f"{len(seeds)} seeds; baseline {runs[0]} mean {np.mean([np.mean(base[s]) for s in seeds]):.2f}")
    for run, d in zip(runs[1:], data[1:]):
        diffs, wa = [], 0
        for s in seeds:
            n = min(len(base[s]), len(d[s]))
            pairs = [(a, b) for a, b in zip(base[s][:n], d[s][:n]) if a > 0 and b > 0]
            wa += n - len(pairs)
            if pairs:
                diffs.append(100 * np.mean([math.log(b / a) for a, b in pairs]))
        x = np.array(diffs)
        print(f"{run}: {x.mean():+.4f} ± {x.std(ddof=1) / math.sqrt(len(x)):.4f}%  win/tie/loss {int((x < 0).sum())}/{int((x == 0).sum())}/{int((x > 0).sum())}"
              f"  mean {np.mean([np.mean(d[s]) for s in seeds]):.2f}  WA {wa}")


if __name__ == "__main__":
    main()
