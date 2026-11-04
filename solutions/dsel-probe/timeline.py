#!/usr/bin/env python3
"""Where along the 1024 requests do the designs of one case differ? (dsel-probe)

Usage: timeline.py LIST   (LIST as for variance.py)

Reads the moves of every request from the out files of the orders runs (all order sequences), and
splits the design effect (moves of a design minus the mean of the case's designs, per request) by
ranges of the request index. A design that is better only through its initial stack differs early;
a design with a better steady state differs everywhere.
"""
import json
import sys
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")
K = 192
RANGES = [(0, 10), (10, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, 700), (700, 1024)]


def request_moves(path):
    lines = path.read_text().split("\n")
    i, moves = K, []
    while i < len(lines) and lines[i].strip():
        n = int(lines[i])
        moves.append(n)
        i += 1 + n
    return moves


def main():
    lst = Path(sys.argv[1])
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    salts = [int(r[0]) for r in rows]
    per = {}  # (salt, seed) -> mean moves per request over the order sequences (array 1024)
    seeds = None
    for salt, _, orders_run in rows:
        run = RUNS / orders_run
        meta = json.loads((run / "meta.json").read_text())
        n_orders = meta.get("design_from", {}).get("orders", 1)
        cases = json.loads((run / "result.json").read_text())["cases"]
        ss = [c["seed"] for c in cases]
        seeds = ss if seeds is None else sorted(set(seeds) & set(ss))
        for seed in ss:
            acc = None
            for j in range(n_orders):
                p = run / "out" / f"{seed:04d}.txt" if j == 0 else run / "orders" / str(j) / "out" / f"{seed:04d}.txt"
                m = np.array(request_moves(p), dtype=float)
                acc = m if acc is None else acc + m
            per[(int(salt), seed)] = acc / n_orders
    M = np.array([[per[(s, c)] for s in salts] for c in seeds])  # case x design x request
    D = M - M.mean(axis=1, keepdims=True)
    # rank the designs of each case by their total over all requests
    tot = M.sum(axis=2)
    best = tot.argmin(axis=1)
    worst = tot.argmax(axis=1)
    idx = np.arange(len(seeds))
    print(f"{len(seeds)} cases x {len(salts)} designs")
    print(f"{'requests':>12s} {'sd of design effect (moves/req)':>32s} {'best-mean':>10s} {'worst-mean':>11s} {'share of total best gap':>24s}")
    gap_total = (D[idx, best, :].sum(axis=1)).mean()
    for a, b in RANGES:
        seg = D[:, :, a:b]
        sd = seg.mean(axis=2).std()
        bm = seg[idx, best, :].mean()
        wm = seg[idx, worst, :].mean()
        share = seg[idx, best, :].sum(axis=1).mean() / gap_total
        print(f"{a:5d}-{b:<6d} {sd:32.4f} {bm:+10.4f} {wm:+11.4f} {share:24.3f}")
    print(f"mean total gap best - mean: {gap_total:+.2f} moves per case")
    # the same split for the selection by the first half of the requests (in-sample bias free check)
    first = M[:, :, :512].sum(axis=2)
    pick = first.argmin(axis=1)
    later = D[idx, pick, 512:].mean()
    print(f"choose by requests 0-511, effect on 512-1023: {later:+.4f} moves/req (vs mean of designs)")


if __name__ == "__main__":
    main()
