"""Nonlinear check of the near-tie correction: gradient boosting on the same state features (and the length),
trained on one run's seeds and applied to another's (open-loop gain as in tie_fit.py). Offline study only.

Usage: python tie_gbm.py TRAIN_RUN A-B VALID_RUN C-D [--gap G]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402
import tie_fit  # noqa: E402

USE = list(range(8))  # fc nc gb nf nfb wtop wfill other (common to both feature layouts)


def rows(ds, gap):
    X, y = [], []
    for seed, r, src, ln, val, T, F, *_ in ds:
        m = T.mean(axis=1)
        for i in range(1, len(src)):
            g = val[i] - val[0]
            if g >= gap:
                continue
            X.append(np.concatenate([F[i, USE] - F[0, USE], F[0, USE], [ln[i] - ln[0], g]]))
            y.append(m[i] - m[0])
    return np.array(X), np.array(y)


def evaluate(ds, total, model, gap):
    # batch the predictions of all near-tie alternatives, then choose per decision
    xs, idx = [], []
    for di, (seed, r, src, ln, val, T, F, *_) in enumerate(ds):
        for i in range(1, len(src)):
            g = val[i] - val[0]
            if g < gap:
                xs.append(np.concatenate([F[i, USE] - F[0, USE], F[0, USE], [ln[i] - ln[0], g]]))
                idx.append((di, i))
    pred = model.predict(np.array(xs)) if xs else np.array([])
    best = {}
    for (di, i), p in zip(idx, pred):
        if p < best.get(di, (0, 0.0))[1]:
            best[di] = (i, p)
    gains, per_seed, changed = [], {}, 0
    for di, (seed, r, src, ln, val, T, F, *_) in enumerate(ds):
        i = best.get(di, (0, 0.0))[0]
        gain = T[0].mean() - T[i].mean()
        gains.append(gain)
        changed += i != 0
        per_seed.setdefault(seed, []).append(gain)
    means = np.array([np.mean(v) for v in per_seed.values()])
    g = np.array(gains)
    return g.sum() / total, means.std(ddof=1) / math.sqrt(len(means)) * len(g) / total, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train_run")
    ap.add_argument("train_seeds")
    ap.add_argument("valid_run")
    ap.add_argument("valid_seeds")
    ap.add_argument("--gap", type=float, default=0.3)
    args = ap.parse_args()
    a, b = map(int, args.train_seeds.split("-"))
    c, d = map(int, args.valid_seeds.split("-"))
    tr, ntr = tie_fit.load(replay.resolve_run(args.train_run), range(a, b + 1))
    va, nva = tie_fit.load(replay.resolve_run(args.valid_run), range(c, d + 1))
    X, y = rows(tr, args.gap)
    for depth, iters in [(3, 100), (4, 200)]:
        model = HistGradientBoostingRegressor(max_depth=depth, max_iter=iters, learning_rate=0.05,
                                              min_samples_leaf=200, l2_regularization=1.0, random_state=1)
        model.fit(X, y)
        gv, se, ch = evaluate(va, nva, model, args.gap)
        print(f"GBM depth {depth} iters {iters}: valid gain per decision {gv:+.5f} +- {se:.5f} (changed {ch})")


if __name__ == "__main__":
    main()
