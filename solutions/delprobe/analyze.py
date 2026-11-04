#!/usr/bin/env python3
"""Calibration of the state value on the shortening trials of the post-processing (delprobe).

Usage: analyze.py RUN [RUN...]

Reads the `#dprobe` lines of the err files (format in README.md). For every probe: predicted
difference (trial - current best) of plan_cost, and the realized difference = moves of the request +
the mean over the rollouts of the moves of the following requests + the difference of the terminal
state values. Prints the calibration overall, by kind and by the predicted difference.
"""
import sys
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")


def load(run):
    rows = []
    for f in sorted((RUNS / run / "err").glob("*.txt")):
        seed = int(f.stem)
        for line in f.read_text().splitlines():
            if not line.startswith("#dprobe "):
                continue
            v = line.split()[1:]
            r, u, kind, lb, lt = map(int, v[:5])
            vb, vt = float(v[5]), float(v[6])
            pb = list(map(float, v[7:11]))
            pt = list(map(float, v[11:15]))
            extra = {}
            if len(v) > 15 and not v[19].lstrip('-').isdigit():  # the format with filler counts and labels
                extra = dict(nfb=int(v[15]), nft=int(v[16]), nbb=int(v[17]), nbt=int(v[18]), labels=v[19])
                rest = v[20:]
            else:
                rest = v[15:]
            seqs = [(int(rest[i]), int(rest[i + 1]), float(rest[i + 2]), float(rest[i + 3])) for i in range(0, len(rest), 4)]
            rows.append(dict(seed=seed, r=r, u=u, kind=kind, lb=lb, lt=lt, vb=vb, vt=vt, pb=pb, pt=pt, seqs=seqs, **extra))
    return rows


def main():
    rows = []
    for run in sys.argv[1:]:
        rows += load(run)
    n = len(rows)
    dlen = np.array([x["lt"] - x["lb"] for x in rows], float)
    pred = np.array([x["vt"] - x["vb"] for x in rows])
    dparts = np.array([[c - b for b, c in zip(x["pb"], x["pt"])] for x in rows])
    later = np.array([np.mean([mt - mb for mb, mt, tb, tt in x["seqs"]]) for x in rows])
    term = np.array([np.mean([tt - tb for mb, mt, tb, tt in x["seqs"]]) for x in rows])
    real = dlen + later + term
    kind = np.array([x["kind"] for x in rows])
    acc = pred < -1e-8
    print(f"{n} probes; accepted (pred < 0) {acc.sum()}")
    print(f"check: pred - dlen - sum(parts) mean {np.mean(pred - dlen - dparts.sum(1)):+.5f} (sd {np.std(pred - dlen - dparts.sum(1)):.5f})")
    ps = pred - dlen
    rs = real - dlen
    print(f"state part: predicted {ps.mean():+.4f}, realized {rs.mean():+.4f} ± {rs.std() / np.sqrt(n):.4f}; terminal {term.mean():+.4f}")
    X = np.column_stack([ps, np.ones(n)])
    coef, *_ = np.linalg.lstsq(X, rs, rcond=None)
    res = rs - X @ coef
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * res.var()))
    print(f"realized state ~ predicted state: slope {coef[0]:.3f} ± {se[0]:.3f}, intercept {coef[1]:+.3f} ± {se[1]:.3f}, residual sd {res.std():.3f}")
    X = np.column_stack([dparts, np.ones(n)])
    coef, *_ = np.linalg.lstsq(X, rs, rcond=None)
    res = rs - X @ coef
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * res.var()))
    names = ["one-step digs", "one-step fixes", "column MDP", "filler charge", "intercept"]
    print("realized state ~ parts:")
    for nm, c, e, i in zip(names, coef, se, range(5)):
        sd = dparts[:, i].std() if i < 4 else 0
        print(f"  {nm:15s} {c:+.3f} ± {e:.3f}  (mean diff {dparts[:, i].mean() if i < 4 else 0:+.4f}, sd {sd:.3f})")
    print("by kind (1 eject pass, 2 neutral collection, 4*operator):")
    for k in sorted(set(kind)):
        m = kind == k
        print(f"  kind {k:2d}: n {m.sum():6d}  dlen {dlen[m].mean():+.3f}  pred state {ps[m].mean():+.4f}  real state {rs[m].mean():+.4f} ± {rs[m].std() / np.sqrt(m.sum()):.4f}  accepted {acc[m].mean():.3f}")
    print("by dlen:")
    for d in sorted(set(dlen)):
        m = dlen == d
        if m.sum() < 30: continue
        print(f"  dlen {d:+.0f}: n {m.sum():6d}  pred state {ps[m].mean():+.4f}  real state {rs[m].mean():+.4f} ± {rs[m].std() / np.sqrt(m.sum()):.4f}")
    if "labels" in rows[0]:
        from collections import Counter
        labels = np.array([x["labels"] for x in rows])
        print("by label difference (top 15):")
        for lab, c in Counter(labels).most_common(15):
            m = labels == lab
            print(f"  {lab:28s} n {m.sum():6d}  pred state {ps[m].mean():+.4f}  real state {rs[m].mean():+.4f} ± {rs[m].std() / np.sqrt(m.sum()):.4f}  ratio {rs[m].mean() / ps[m].mean() if abs(ps[m].mean()) > 1e-6 else float('nan'):.3f}  accepted {acc[m].mean():.3f}")
        dnf = np.array([x["nft"] - x["nfb"] for x in rows])
        dnb = np.array([x["nbt"] - x["nbb"] for x in rows])
        nfb = np.array([x["nfb"] for x in rows])
        print("by filler count change (trial - best) and below-generic change:")
        for a in sorted(set(dnf)):
            for b in sorted(set(dnb)):
                m = (dnf == a) & (dnb == b)
                if m.sum() < 50: continue
                print(f"  dfillers {a:+d} dbelow {b:+d}: n {m.sum():6d}  pred state {ps[m].mean():+.4f}  real state {rs[m].mean():+.4f} ± {rs[m].std() / np.sqrt(m.sum()):.4f}  filler-charge diff {dparts[m, 3].mean():+.4f}")
        print("by fillers of the best state (for dfillers +1):")
        for a in sorted(set(nfb)):
            m = (nfb == a) & (dnf == 1)
            if m.sum() < 50: continue
            print(f"  fillers {a}: n {m.sum():6d}  pred state {ps[m].mean():+.4f}  real state {rs[m].mean():+.4f} ± {rs[m].std() / np.sqrt(m.sum()):.4f}")
    print("by predicted total difference (decision bins):")
    edges = [-1.5, -1.0, -0.75, -0.5, -0.3, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5]
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (pred >= lo) & (pred < hi)
        if m.sum() < 20: continue
        print(f"  pred [{lo:+.2f},{hi:+.2f}): n {m.sum():6d}  pred {pred[m].mean():+.3f}  real {real[m].mean():+.3f} ± {real[m].std() / np.sqrt(m.sum()):.3f}  (state pred {ps[m].mean():+.3f} real {rs[m].mean():+.3f})")


if __name__ == "__main__":
    main()
