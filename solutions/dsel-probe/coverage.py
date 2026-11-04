#!/usr/bin/env python3
"""Filler coverage of the targets' handle holes by the other papers (dsel-probe).

Usage: coverage.py LIST --seeds A-B [--colfix FILE]   (LIST as for variance.py)

For a target t (paper D in column l) and another paper X of column cX > l, X placed at level c'
(just above the top of column c') shows its colors on the handles h_c'..h_cX where it is opaque and
D is a hole. The best level for X is the shallowest c' such that X agrees with A_t on every hole of D
in [c', cX] where X is opaque (the run of agreement ending at cX, counted in holes of D). Its gain is
the number of holes of D it covers. Design features (per design, mean over the 256 targets):
  cov_best:   the largest gain over all X;
  cov_top2:   the sum of the two largest gains;
  cov_exp:    sum over X of 2^(gain) / 2^(holes of D) (soft count of long runs);
Prints their within-case correlation with the realized fix moves and the log score.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from colfix import barcode_hash_of_input, load_design  # noqa: E402

RUNS = Path("/home/sato/ahc074/runs")


def design_features(d):
    H = int(d["H"])
    A, cols, ded, handle = d["A"], d["columns"], d["ded"], d["handle"]
    P = d["papers"]
    K = len(cols)
    opq = np.array([[P[2 * k] >> handle[j] & 1 for j in range(H)] for k in range(K)], dtype=np.int8)
    blk = np.array([[P[2 * k + 1] >> handle[j] & 1 for j in range(H)] for k in range(K)], dtype=np.int8)
    col = np.array(cols)
    best, top2, soft = [], [], []
    hbest, hsum = [], []
    idx = np.arange(H)
    head = np.zeros(K, dtype=bool)
    seen = {}
    for k in range(K):
        c = cols[k]
        if c >= 0:
            seen[c] = seen.get(c, 0) + 1
            if seen[c] <= 2:
                head[k] = True
    for t in range(256):
        D = ded[t]
        l = cols[D]
        at = np.array([A[t] >> handle[j] & 1 for j in range(H)], dtype=np.int8)
        hole = (1 - opq[D]).astype(bool)
        nh = int(hole.sum())
        cand = (col > l)
        cand[D] = False
        if not cand.any():
            best.append(0), top2.append(0), soft.append(0.0)
            continue
        o = opq[cand].astype(bool)
        b = blk[cand]
        cX = col[cand]
        inrange = (idx[None, :] > l) & (idx[None, :] <= cX[:, None])
        mism = hole[None, :] & o & (b != at[None, :]) & inrange
        anym = mism.any(axis=1)
        last = H - 1 - np.argmax(mism[:, ::-1], axis=1)
        stop = np.where(anym, last, l)
        cover = (hole[None, :] & o & inrange).astype(np.int32)
        csum = np.concatenate([np.zeros((cover.shape[0], 1), np.int32), np.cumsum(cover, axis=1)], axis=1)
        gains = csum[np.arange(len(cX)), cX + 1] - csum[np.arange(len(cX)), stop + 1]
        hg = gains[head[cand]]
        hbest.append(int(hg.max()) if len(hg) else 0)
        # per column: the best of its two heads, summed over the columns deeper than l
        hc = cX[head[cand]]
        per_col = {}
        for gg, cc in zip(hg, hc):
            per_col[cc] = max(per_col.get(cc, 0), gg)
        hsum.append(float(sum(max(0, v - 1) for v in per_col.values())))
        g = np.sort(gains)[::-1]
        best.append(int(g[0]))
        top2.append(int(g[:2].sum()))
        soft.append(float((2.0 ** g).sum() / 2.0 ** max(nh, 1)))
    return {"cov_best": float(np.mean(best)), "cov_top2": float(np.mean(top2)), "cov_soft": float(np.mean(soft)),
            "head_best": float(np.mean(hbest)), "head_sum": float(np.mean(hsum))}


def main():
    lst = Path(sys.argv[1])
    lo, hi = map(int, sys.argv[sys.argv.index("--seeds") + 1].split("-"))
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    feats = {}
    for salt, design_run, _ in rows:
        for seed in range(lo, hi):
            d = load_design(RUNS / design_run / "design" / f"{barcode_hash_of_input(seed)}.txt")
            feats[f"{salt}:{seed}"] = design_features(d)
    out = lst.with_suffix(f".coverage_{lo}_{hi}.json")
    out.write_text(json.dumps(feats))
    print(f"written {out}")


if __name__ == "__main__":
    main()
