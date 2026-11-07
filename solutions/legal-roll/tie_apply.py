"""Applies saved near-tie weights (tie_fit.py --out JSON, per raw unit) to the decisions of a run and reports
the open-loop gain of the corrected choice (all rollout sequences; the choice does not use them).

Usage: python tie_apply.py WEIGHTS.json RUN SEEDS(A-B) [--gap G] [--margin M]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402
import tie_fit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("weights")
    ap.add_argument("run")
    ap.add_argument("seeds")
    ap.add_argument("--gap", type=float, default=None)
    ap.add_argument("--margin", type=float, default=0.0)
    args = ap.parse_args()
    w = json.load(open(args.weights))
    gap = args.gap if args.gap is not None else w["gap"]
    a, b = map(int, args.seeds.split("-"))
    run = replay.resolve_run(args.run)
    ds, total = tie_fit.load(run, range(a, b + 1))
    names = tie_fit.NAMES + ["lab_" + l for l in tie_fit.LABELS] + tie_fit.EXTRA
    gains, per_seed, changed = [], {}, 0
    for seed, r, src, ln, val, T, F in ds:
        best, bs = 0, -args.margin
        for i in range(1, len(src)):
            g = val[i] - val[0]
            if g >= gap:
                continue
            s = g + w["coef"].get("const", 0.0) + w["coef"].get("len", 0.0) * (ln[i] - ln[0])
            for j, n in enumerate(names[:F.shape[1]]):
                s += w["coef"].get(n, 0.0) * (F[i, j] - F[0, j])
            if s < bs:
                best, bs = i, s
        gain = T[0].mean() - T[best].mean()
        gains.append(gain)
        changed += best != 0
        per_seed.setdefault(seed, []).append(gain)
    means = np.array([np.mean(v) for v in per_seed.values()])
    g = np.array(gains)
    per_dec = g.sum() / max(total, 1)
    se = means.std(ddof=1) / math.sqrt(len(means)) * len(g) / max(total, 1)
    print(f"{Path(args.weights).name} on {run.name} seeds {args.seeds}: decisions {total} (with alternatives {len(g)}), "
          f"changed {changed}, gain per decision {per_dec:+.5f} +- {se:.5f} moves")


if __name__ == "__main__":
    main()
