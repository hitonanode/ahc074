"""Near-tie correction study on legal-roll ROLL_FEAT runs (`#rollmat` / `#rc` / `#rf` lines).

For each decision, alternative i (0 = the SOTA's choice) has the rollout difference y_i = mean_s(T_i - T_0)
(moves of the request + rollout cost), the plan_cost difference g_i = value_i - value_0 (>= 0) and the
feature differences d_i = f_i - f_0. A linear correction r_i = y_i - g_i ~ w . d_i is fitted on the training
seeds (ridge, near-ties g_i < GAP only). On the validation seeds the corrected choice (argmin of g_i + w . d_i,
the SOTA's choice at 0, switching only below -MARGIN) is scored with all rollout sequences (the choice does
not use them, so the gain is unbiased).

Usage: python tie_fit.py RUN [--train 0-99] [--valid 100-199] [--gap 0.3] [--ridge 1.0]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

NAMES = ["fc", "nc", "gb", "nf", "nfb", "wtop", "wfill", "other"]
LABELS = ["other", "ret", "fret", "reuse", "relevel", "gen", "dig", "lift", "fdig", "fill", "hdig", "help", "fix", "repair"]
EXTRA = ["stay", "genmv", "lvl", "ncdig", "nchand", "ncmdp"]  # stay..lvl from 06:40 (legal-roll-feat2), nc parts from legal-roll3
EVERY_DEFAULT = [12]  # decisions per request for make_roll2.py runs (ROLL_EVERY), set by --every


def load(run_dir: Path, seeds: range):
    """decisions: (seed, r, src, length, value, T[n, S], F[n, nfeat]); and the total number of decisions."""
    out = []
    total = 0
    dirs = [run_dir / "err"]
    if (run_dir / "orders").is_dir():
        dirs += [d / "err" for d in sorted((run_dir / "orders").iterdir())]
    paths = [(seed, d / f"{seed:04d}.txt") for d in dirs for seed in seeds]
    for seed, path in paths:
        if not path.exists():
            continue
        lines = path.read_text(errors="replace").splitlines()
        found = False
        for line in lines:
            if line.startswith("roll_decisions = "):
                total += int(line.split()[2])
                found = True
        if not found:
            # make_roll2.py runs: a decision at every ROLL_EVERY-th request (12 unless the file says otherwise)
            total += -(-1024 // EVERY_DEFAULT[0])
        i = 0
        while i < len(lines):
            if lines[i].startswith("#rollmat "):
                tok = lines[i].split()
                r, n = tok[1], int(tok[3])
                chosen = int(tok[4]) if len(tok) > 4 else 0  # the policy's choice (make_roll2.py runs)
                src, ln, val, T, F = [], [], [], [], []
                for j in range(n):
                    rc = lines[i + 1 + 2 * j].split()
                    rf = lines[i + 2 + 2 * j].split()
                    assert rc[0] == "#rc" and rf[0] == "#rf", (seed, r)
                    src.append(int(rc[1]))
                    ln.append(int(rc[2]))
                    val.append(float(rc[3]))
                    T.append([int(rc[2]) + float(x) for x in rc[4:]])
                    F.append([float(x) for x in rf[1:]])
                out.append((seed, int(r), np.array(src), np.array(ln), np.array(val), np.array(T), np.array(F), chosen))
                i += 1 + 2 * n
            else:
                i += 1
    return out, total


def design(ds, gap):
    """Rows (alternatives) of the near-tie regression: X = [d features, d length], target r = y - g."""
    X, y, g = [], [], []
    for seed, r, src, ln, val, T, F, *_ in ds:
        m = T.mean(axis=1)
        for i in range(1, len(src)):
            gi = val[i] - val[0]
            if gi >= gap:
                continue
            d = np.concatenate([F[i] - F[0], [ln[i] - ln[0]]])
            X.append(d)
            y.append((m[i] - m[0]) - gi)
            g.append(gi)
    return np.array(X), np.array(y), np.array(g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--valid-run", default="", help="the run of the validation seeds (default: the same run)")
    ap.add_argument("--train", default="0-99")
    ap.add_argument("--valid", default="100-199")
    ap.add_argument("--gap", type=float, default=0.3)
    ap.add_argument("--ridge", type=float, default=1.0)
    ap.add_argument("--nolabels", action="store_true", help="state features and the length only (no move labels)")
    ap.add_argument("--out", default="", help="write the weights (per raw unit) to this JSON file")
    ap.add_argument("--noextra", action="store_true", help="without the extra features (stay, genmv, lvl)")
    ap.add_argument("--every", type=int, default=12, help="ROLL_EVERY of make_roll2.py runs (for the decision count)")
    ap.add_argument("--features", default="", help="comma list of the features to use (default: all kept by the flags)")
    args = ap.parse_args()
    run = replay.resolve_run(args.run)
    EVERY_DEFAULT[0] = args.every
    a, b = map(int, args.train.split("-"))
    c, d = map(int, args.valid.split("-"))
    train, ntrain = load(run, range(a, b + 1))
    vrun = replay.resolve_run(args.valid_run) if args.valid_run else run
    valid, nvalid = load(vrun, range(c, d + 1))
    print(f"{run.name}: train decisions with alternatives {len(train)} (of {ntrain}), valid {len(valid)} (of {nvalid})")
    X, y, g = design(train, args.gap)
    names = (NAMES + ["lab_" + l for l in LABELS] + EXTRA)[:X.shape[1] - 1] + ["len"]
    keep = X.std(axis=0) > 1e-9
    if args.nolabels:
        keep &= np.array([not n.startswith("lab_") for n in names])
    if args.noextra:
        keep &= np.array([n not in EXTRA for n in names])
    if args.features:
        want = set(args.features.split(","))
        keep &= np.array([n in want for n in names])
    X = X[:, keep]
    names = [n for n, k in zip(names, keep) if k]
    sd = X.std(axis=0)
    Z = np.hstack([X / sd, np.ones((len(X), 1))])
    pen = args.ridge * np.eye(Z.shape[1])
    pen[-1, -1] = 1e-9  # the intercept is not penalized
    w = np.linalg.solve(Z.T @ Z + pen, Z.T @ y)
    pred = Z @ w
    names = names + ["const"]
    sd = np.concatenate([sd, [1.0]])
    print(f"  train near-tie alternatives {len(y)}: residual mean {y.mean():+.4f}, R^2 of the correction "
          f"{1 - np.var(y - pred) / np.var(y):.4f}")
    for n, wi, s in sorted(zip(names, w, sd), key=lambda t: -abs(t[1])):
        print(f"    {n:12s} coef per sd {wi:+.4f} (sd {s:.3f})")
    full_keep = keep

    def run_valid(ds, total, label):
        Xv, yv, gv = design(ds, args.gap)
        Xv = np.hstack([Xv[:, full_keep], np.ones((len(Xv), 1))])
        pv = (Xv / sd) @ w
        cor = np.corrcoef(pv, yv)[0, 1] if len(yv) > 2 else float("nan")
        print(f"  {label}: near-tie alternatives {len(yv)}, corr(pred, residual) {cor:+.4f}")
        for margin in [0.0, 0.05, 0.1, 0.2]:
            gains, changed, per_seed = choose_masked(ds, w, sd, args.gap, margin, full_keep)
            means = np.array([np.mean(v) for v in per_seed.values()])
            per_dec = gains.sum() / max(total, 1)
            se = means.std(ddof=1) / math.sqrt(len(means)) * len(gains) / max(total, 1)
            print(f"    margin {margin:.2f}: changed {changed} of {len(gains)} decisions with alternatives; "
                  f"gain per decision (all {total}) {per_dec:+.5f} +- {se:.5f} moves")

    def choose_masked(ds, w, sd, gap, margin, keep):
        gains, changed, per_seed = [], 0, {}
        for seed, r, src, ln, val, T, F, *_ in ds:
            best, bs = 0, -margin
            for i in range(1, len(src)):
                gi = val[i] - val[0]
                if gi >= gap:
                    continue
                dvec = np.concatenate([np.concatenate([F[i] - F[0], [ln[i] - ln[0]]])[keep], [1.0]]) / sd
                s = gi + float(dvec @ w)
                if s < bs:
                    best, bs = i, s
            gain = T[0].mean() - T[best].mean()
            gains.append(gain)
            changed += best != 0
            per_seed.setdefault(seed, []).append(gain)
        return np.array(gains), changed, per_seed

    if args.out:
        import json
        coef = {n: float(wi / si) for n, wi, si in zip(names, w, sd)}
        json.dump({"coef": coef, "gap": args.gap, "nolabels": args.nolabels}, open(args.out, "w"), indent=1)
        print(f"  weights per raw unit written to {args.out}")
    run_valid(train, ntrain, "train (in sample)")
    run_valid(valid, nvalid, "valid (out of sample)")
    # reference: the rollout oracle with half of the sequences to select and the other half to measure
    for label, ds, total in [("train", train, ntrain), ("valid", valid, nvalid)]:
        rng = np.random.default_rng(1)
        tot = 0.0
        for seed, r, src, ln, val, T, F, *_ in ds:
            S = T.shape[1]
            g = 0.0
            for _ in range(10):
                perm = rng.permutation(S)
                h = S // 2
                i = int(np.argmin(T[:, perm[:h]].mean(axis=1)))
                g += T[0, perm[h:]].mean() - T[i, perm[h:]].mean()
            tot += g / 10
        print(f"  {label}: rollout selection on half of the sequences, gain per decision (all) {tot / max(total, 1):+.5f}")


if __name__ == "__main__":
    main()
