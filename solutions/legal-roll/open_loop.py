"""Open-loop analysis of legal-roll ROLL_MODE 8 runs (`#rollmat` / `#rc` lines).

Each decision has candidates i (0 = the SOTA's choice) with costs T[i, s] = moves of the request + rollout cost
on common sequence s (moves of the next requests + 2K per wrong display + terminal plan_cost(0)).
For a selection size k, the choice is made on k random sequences and its gain over the SOTA's choice is
measured on the other sequences (unbiased for that selection rule). Repeated splits are averaged.

Usage: python open_loop.py RUN [--sources 1,2,3,4] [--splits 20]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def err_files(run_dir: Path):
    yield from sorted((run_dir / "err").glob("*.txt"))
    orders = run_dir / "orders"
    if orders.is_dir():
        for j in sorted(orders.iterdir()):
            yield from sorted((j / "err").glob("*.txt"))


TOTAL_DECISIONS = [0]


def load(run_dir: Path):
    decisions = []  # (case id, r, sources, lens, values, T matrix)
    for case, path in enumerate(err_files(run_dir)):
        lines = path.read_text(errors="replace").splitlines()
        for line in lines:
            if line.startswith("roll_decisions = "):
                TOTAL_DECISIONS[0] += int(line.split()[2])
        i = 0
        while i < len(lines):
            if lines[i].startswith("#rollmat "):
                _, r, u, n = lines[i].split()
                n = int(n)
                rows = [lines[i + 1 + j].split() for j in range(n)]
                src = np.array([int(t[1]) for t in rows])
                ln = np.array([int(t[2]) for t in rows], dtype=float)
                val = np.array([float(t[3]) for t in rows])
                cost = np.array([[float(x) for x in t[4:]] for t in rows])
                decisions.append((case, int(r), src, ln, val, ln[:, None] + cost))
                i += 1 + n
            else:
                i += 1
    return decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--sources", default="1,2,3,4", help="candidate sources besides the SOTA's choice")
    ap.add_argument("--splits", type=int, default=20)
    args = ap.parse_args()
    run = replay.resolve_run(args.run)
    allowed = {int(x) for x in args.sources.split(",")}
    dec = load(run)
    rng = np.random.default_rng(1)
    S = dec[0][5].shape[1] if dec else 0
    print(f"{run.name}: {len(dec)} decisions, {S} sequences each")
    # restrict candidates
    data = []
    for case, r, src, ln, val, T in dec:
        keep = [0] + [i for i in range(1, len(src)) if src[i] in allowed]
        data.append((case, r, src[keep], ln[keep], val[keep], T[keep]))
    ncand = np.array([len(d[2]) for d in data])
    print(f"  candidates per decision (incl. the SOTA's): mean {ncand.mean():.2f}, with alternatives {np.mean(ncand > 1):.3f}")
    # gaps: mean over all sequences of T[0] - T[i] for each alternative (positive: the alternative is better)
    diffs = {s: [] for s in sorted(allowed)}
    best_any = []
    for case, r, src, ln, val, T in data:
        if len(src) < 2:
            continue
        m = T.mean(axis=1)
        for i in range(1, len(src)):
            diffs[int(src[i])].append(m[0] - m[i])
    for s, xs in diffs.items():
        if xs:
            xs = np.array(xs)
            print(f"  source {s}: {len(xs)} alternatives, mean (SOTA - alt) {xs.mean():+.4f} +- {xs.std(ddof=1) / math.sqrt(len(xs)):.4f}, "
                  f"share better {np.mean(xs > 0):.3f}")
    # selection with k sequences, evaluation on the rest
    print("  selection on k sequences, gain over the SOTA's choice measured on the other sequences (per decision):")
    curve = {}
    for k in [1, 2, 4, 8, 16, 24, 32, 40, 64, 80]:
        if k >= S:
            continue
        gains = []
        changed = []
        for case, r, src, ln, val, T in data:
            if len(src) < 2:
                gains.append(0.0)
                changed.append(0.0)
                continue
            g = 0.0
            c = 0.0
            for _ in range(args.splits):
                perm = rng.permutation(S)
                a, b = perm[:k], perm[k:]
                i = int(np.argmin(T[:, a].mean(axis=1)))
                g += T[0, b].mean() - T[i, b].mean()
                c += i != 0
            gains.append(g / args.splits)
            changed.append(c / args.splits)
        gains = np.array(gains)
        # SE over cases (decisions of a case are correlated through the design)
        cases = np.array([d[0] for d in data])
        per_case = np.array([gains[cases == c].mean() for c in np.unique(cases)])
        curve[k] = gains.mean()
        print(f"    k={k:2d}: gain {gains.mean():+.4f} +- {per_case.std(ddof=1) / math.sqrt(len(per_case)):.4f} moves/decision, "
              f"changed {np.mean(changed):.3f}")
    # extrapolation gain(k) = g_inf - a / k on k >= 8
    ks = [k for k in [8, 16, 24, 32, 40, 64, 80] if k < S and k in curve]
    if len(ks) >= 2 and curve:
        xs = np.array([1.0 / k for k in ks])
        ys = np.array([curve[k] for k in ks])
        A = np.vstack([np.ones_like(xs), -xs]).T
        g_inf, a = np.linalg.lstsq(A, ys, rcond=None)[0]
        print(f"  fit gain(k) = g_inf - a/k on k in {ks}: g_inf {g_inf:+.4f}, a {a:.4f}")
    if TOTAL_DECISIONS[0]:
        share = len(data) / TOTAL_DECISIONS[0]
        print(f"  decisions with alternatives: {len(data)} of {TOTAL_DECISIONS[0]} ({share:.3f}); per decision of any kind multiply by it")
    # the best alternative by all sequences (biased upward: the max over noisy means)
    up = []
    for case, r, src, ln, val, T in data:
        m = T.mean(axis=1)
        up.append(m[0] - m.min())
    print(f"  upper-biased: mean (SOTA - min over candidates, all sequences) {np.mean(up):.4f}")


if __name__ == "__main__":
    main()
