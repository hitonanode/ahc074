#!/usr/bin/env python3
"""The filler proxy of esw-fixiter's filler_climb, recomputed on the saved (final) designs (dsel-probe).

Usage: proxy.py LIST --seeds A-B

Design::filler_climb's proxy: for every column c, the probability that its head shows color b times
the utility of the strongest eligible paper of color b there (the largest weight, pairs ahead of
singles), summed; the utility of a paper is its filler_gain summed over the 256 targets. Recomputed
here from the saved design state (after the rematch and the perforation), with variants:
  proxy_final:   the same formula (holes of the targets from the printed papers);
  proxy_heads2:  every column's two printed head papers (the initial top two) instead of the
                 strongest eligible ones;
Writes LIST.proxy_A_B.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from colfix import barcode_hash_of_input, load_design  # noqa: E402

RUNS = Path("/home/sato/ahc074/runs")


def low_bits(n):
    return (1 << n) - 1 if n > 0 else 0


def filler_gain(tb, l, targetdiff, yb, dy, c, q):
    if c == l:
        return 0.0
    holes = ~low_bits(l + 1) | targetdiff
    rng = low_bits(c + 1) & ~dy & holes
    mis = (yb ^ tb) & rng
    level = mis.bit_length() if mis else 0
    if level > c:
        return 0.0
    covered = rng & low_bits(c) & ~low_bits(level)
    p0, p1, expected = 1.0, 0.0, 0.0
    z = covered
    while z:
        j = (z & -z).bit_length() - 1
        z &= z - 1
        p = 0.5 * (q[j + 1] - q[j])
        expected += p
        p1 = p1 * (1 - p) + p0 * p
        p0 *= 1 - p
    return max(0.0, expected - (1 - p0) - 0.6 * (1 - p0 - p1))


def proxies(d):
    H = int(d["H"])
    A, cols, ded, handle = d["A"], d["columns"], d["ded"], d["handle"]
    hb = [sum((A[t] >> handle[j] & 1) << j for j in range(H)) for t in range(256)]
    units = {}
    for t in range(256):
        units.setdefault(ded[t], []).append(t)
    unit_list = sorted(units)  # papers
    col_of_t = [cols[ded[t]] for t in range(256)]
    diff_of_paper = {k: (hb[ts[0]] ^ hb[ts[1]]) if len(ts) == 2 else 0 for k, ts in units.items()}
    # hole counts per handle by color (as Design::hn) and nt
    hn = [[0, 0] for _ in range(H)]
    nt = [0] * H
    for t in range(256):
        c = col_of_t[t]
        nt[c] += 1
        holes = (low_bits(H) & ~low_bits(c + 1)) | diff_of_paper[ded[t]]
        for j in range(H):
            if holes >> j & 1:
                hn[j][hb[t] >> j & 1] += 1
    cp = []
    for c in range(H):
        x, y, tt = hn[c][0], hn[c][1], 2.0 * nt[c]
        n = x + y + tt
        p = (y + tt * (y > x)) / n if n else 0.5
        cp.append((1 - p, p))
    q = []
    for t in range(256):
        qq = [0.0] * (H + 1)
        for c in range(H):
            qq[c + 1] = qq[c] + 2 * cp[c][(hb[t] >> c & 1) ^ 1]
        q.append(qq)
    utility = {}
    for k in unit_list:
        ts = units[k]
        c = cols[k]
        yb = hb[ts[0]]
        dy = diff_of_paper[k]
        s = 0.0
        for t in range(256):
            s += filler_gain(hb[t], col_of_t[t], diff_of_paper[ded[t]], yb, dy, c, q[t])
        utility[k] = s
    # proxy_final: strongest eligible paper of each color per column
    proxy_final = 0.0
    proxy_heads2 = 0.0
    proxy_mean = 0.0
    proxy_wmean = 0.0
    by_col = {}
    for k in unit_list:
        by_col.setdefault(cols[k], []).append(k)
    for c, ks in by_col.items():
        best = [0.0, 0.0]
        wmax = [0, 0]
        for k in ks:
            b = hb[units[k][0]] >> c & 1
            wmax[b] = max(wmax[b], len(units[k]))
        cnt = [0, 0]
        for k in ks:
            b = hb[units[k][0]] >> c & 1
            cnt[b] += 1
            if len(units[k]) == wmax[b]:
                best[b] = max(best[b], utility[k])
        proxy_final += sum(cp[c][b] * best[b] for b in range(2) if cnt[b])
        heads = sorted(ks)[:2]  # printed order: the internal numbers increase down the column
        hv = [0.0, 0.0]
        for k in heads:
            b = hb[units[k][0]] >> c & 1
            hv[b] = max(hv[b], utility[k])
        proxy_heads2 += sum(cp[c][b] * hv[b] for b in range(2))
        # mean utility of the units of each color (every unit of that color equally likely on top)
        mv = [[], []]
        for k in ks:
            mv[hb[units[k][0]] >> c & 1].append(utility[k])
        proxy_mean += sum(cp[c][b] * (sum(mv[b]) / len(mv[b])) for b in range(2) if mv[b])
        # utility-weighted by the targets served (pairs twice): a paper requested more is more often out
        wv = [[0.0, 0.0], [0.0, 0.0]]
        for k in ks:
            b = hb[units[k][0]] >> c & 1
            wv[b][0] += len(units[k]) * utility[k]
            wv[b][1] += len(units[k])
        proxy_wmean += sum(cp[c][b] * wv[b][0] / wv[b][1] for b in range(2) if wv[b][1])
    return {"proxy_final": proxy_final / 256, "proxy_heads2": proxy_heads2 / 256,
            "proxy_mean": proxy_mean / 256, "proxy_wmean": proxy_wmean / 256,
            "utility_mean": float(np.mean(list(utility.values())))}


def main():
    lst = Path(sys.argv[1])
    lo, hi = map(int, sys.argv[sys.argv.index("--seeds") + 1].split("-"))
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    feats = {}
    for salt, design_run, _ in rows:
        for seed in range(lo, hi):
            d = load_design(RUNS / design_run / "design" / f"{barcode_hash_of_input(seed)}.txt")
            feats[f"{salt}:{seed}"] = proxies(d)
    out = lst.with_suffix(f".proxy_{lo}_{hi}.json")
    out.write_text(json.dumps(feats))
    print(f"written {out}")


if __name__ == "__main__":
    main()
