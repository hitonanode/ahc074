#!/usr/bin/env python3
"""Calibration of the state value used by the neutral search (valprobe).

Usage: analyze.py RUN [RUN...]

Reads the `#vprobe` lines of the err files. For every probe: predicted difference
(chosen - baseline) of plan_cost = moves of the request + the four parts of the state value
(one-step digs, one-step fixes, column MDP term, filler charge), and the realized difference =
moves of the request + the mean over the rollouts of the moves of the following requests + the
difference of the terminal state values. Prints the regression of the realized difference on the
predicted parts (slope 1 = calibrated part) and summaries.
"""
import sys
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")


def load(run):
    rows = []
    for f in sorted((RUNS / run / "err").glob("*.txt")):
        for line in f.read_text().splitlines():
            if not line.startswith("#vprobe "):
                continue
            v = line.split()[1:]
            r, u, lb, lc = map(int, v[:4])
            pb = list(map(float, v[4:8]))
            pc = list(map(float, v[8:12]))
            rest = v[12:]
            seqs = [(int(rest[i]), int(rest[i + 1]), float(rest[i + 2]), float(rest[i + 3])) for i in range(0, len(rest), 4)]
            rows.append((lb, lc, pb, pc, seqs))
    return rows


def main():
    rows = []
    for run in sys.argv[1:]:
        rows += load(run)
    n = len(rows)
    dlen = np.array([lc - lb for lb, lc, _, _, _ in rows], dtype=float)
    dparts = np.array([[c - b for b, c in zip(pb, pc)] for _, _, pb, pc, _ in rows])
    realized = np.array([lc - lb + np.mean([mc - mb + tc - tb for mb, mc, tb, tc in seqs]) for lb, lc, _, _, seqs in rows])
    future = np.array([np.mean([mc - mb for mb, mc, tb, tc in seqs]) for *_, seqs in rows])
    terminal = np.array([np.mean([tc - tb for mb, mc, tb, tc in seqs]) for *_, seqs in rows])
    pred = dlen + dparts.sum(axis=1)
    print(f"{n} probes")
    print(f"mean predicted diff {pred.mean():+.4f} (moves {dlen.mean():+.4f}, parts {dparts.mean(axis=0).round(4)})")
    print(f"mean realized diff  {realized.mean():+.4f} ± {realized.std() / np.sqrt(n):.4f} (request {dlen.mean():+.4f}, "
          f"later moves {future.mean():+.4f}, terminal {terminal.mean():+.4f})")
    state_pred = dparts.sum(axis=1)
    state_real = future + terminal
    print(f"state part: predicted {state_pred.mean():+.4f}, realized {state_real.mean():+.4f} ± {state_real.std() / np.sqrt(n):.4f}")
    # regression of the realized later cost on the predicted parts
    X = np.column_stack([dparts, np.ones(n)])
    coef, *_ = np.linalg.lstsq(X, state_real, rcond=None)
    res = state_real - X @ coef
    cov = np.linalg.inv(X.T @ X) * res.var()
    se = np.sqrt(np.diag(cov))
    names = ["one-step digs", "one-step fixes", "column MDP", "filler charge", "intercept"]
    print("regression realized(later moves + terminal) ~ predicted parts:")
    for nm, c, e in zip(names, coef, se):
        print(f"  {nm:16s} {c:+.3f} ± {e:.3f}   (sd of the part diff {dparts[:, names.index(nm)].std() if nm != 'intercept' else 0:.3f})")
    print(f"  R2 {1 - res.var() / state_real.var():.4f}; residual sd {res.std():.3f}")
    # same-length probes only
    same = dlen == 0
    print(f"same-length probes {same.sum()}: predicted state diff {state_pred[same].mean():+.4f}, realized {state_real[same].mean():+.4f} ± {state_real[same].std() / np.sqrt(same.sum()):.4f}")
    shorter = dlen < 0
    print(f"shorter probes {shorter.sum()}: request {dlen[shorter].mean():+.3f}, predicted state {state_pred[shorter].mean():+.4f}, realized state {state_real[shorter].mean():+.4f} ± {state_real[shorter].std() / np.sqrt(max(shorter.sum(), 1)):.4f}")


if __name__ == "__main__":
    main()
