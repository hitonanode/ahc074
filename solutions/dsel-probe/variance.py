#!/usr/bin/env python3
"""Design-seed variance of dsel-probe (solutions/dsel-probe/README.md).

Usage: variance.py LIST  (LIST: lines "salt design_run orders_run", as printed by run_salts.sh)

For every case c, design (salt) s and order sequence j, y = log(score) (the orders runs evaluate the
saved designs of design_run on the same order sequences j = 0..n-1). Model within a case:
    y[s, j] = mu + o[j] + d[s] + e[s, j]
d: the design effect, o: the order-sequence effect shared by the designs (common random numbers).
Prints the variance components, the expected gain of choosing the best of k designs with exact
knowledge, and with selection on half of the order sequences (validated on the other half).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")


def load_orders(run):
    cases = json.loads((RUNS / run / "result.json").read_text())["cases"]
    return {c["seed"]: c.get("order_scores") or [c["score"]] for c in cases}


def main():
    rows = [line.split() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    data = {}
    for salt, design_run, orders_run in rows:
        data[int(salt)] = load_orders(orders_run)
    salts = sorted(data)
    seeds = sorted(set.intersection(*(set(v) for v in data.values())))
    n_o = min(len(data[s][c]) for s in salts for c in seeds)
    Y = np.array([[[math.log(data[s][c][j]) for j in range(n_o)] for s in salts] for c in seeds]) * 100  # in %
    nc, ns, no = Y.shape
    print(f"cases {nc}, designs {ns}, order sequences {no}")
    if (Y <= 0).any():
        print("WARNING: zero scores (WA)")
    # two-way decomposition within each case
    mu = Y.mean(axis=(1, 2), keepdims=True)
    d = Y.mean(axis=2, keepdims=True) - mu
    o = Y.mean(axis=1, keepdims=True) - mu
    e = Y - mu - d - o
    var_e = (e ** 2).sum() / (nc * (ns - 1) * (no - 1))
    ms_d = no * (d ** 2).sum() / (nc * (ns - 1))
    var_d = (ms_d - var_e) / no
    ms_o = ns * (o ** 2).sum() / (nc * (no - 1))
    var_o = (ms_o - var_e) / ns
    print(f"sd of one run's noise (design x orders interaction e): {math.sqrt(var_e):.3f}%")
    print(f"sd of the order-sequence effect shared by designs (o): {math.sqrt(max(var_o, 0)):.3f}%")
    print(f"sd of the true design effect (d): {math.sqrt(max(var_d, 0)):.3f}%  (raw sd of design means {math.sqrt(ms_d / no):.3f}%)")
    # selection: choose on half of the orders, evaluate on the other half
    half = no // 2
    A = Y[:, :, :half].mean(axis=2)
    B = Y[:, :, half:].mean(axis=2)
    for k in (2, 4, 8):
        if k > ns:
            continue
        gains, oracle = [], []
        for start in range(0, ns - k + 1, k):  # disjoint groups of k designs
            grp = slice(start, start + k)
            for c in range(nc):
                a, b = A[c, grp], B[c, grp]
                base = b[0]  # the first design of the group as the "unselected" one
                pick = int(np.argmin(a))
                gains.append(b[pick] - b.mean())
                oracle.append(b.min() - b.mean())
        g = np.array(gains)
        print(f"best of {k}: choose on {half} orders, check on {no - half}: {g.mean():+.3f} ± {g.std() / math.sqrt(len(g)):.3f}%"
              f" vs the group mean (oracle on the check half {np.mean(oracle):+.3f}%)")
    # the design means
    dm = Y.mean(axis=2)
    out = Path(sys.argv[1]).with_suffix(".design_means.json")
    out.write_text(json.dumps({"salts": salts, "seeds": seeds, "means": dm.tolist(),
                               "A": A.tolist(), "B": B.tolist()}))
    print(f"design means written to {out}")


if __name__ == "__main__":
    main()
