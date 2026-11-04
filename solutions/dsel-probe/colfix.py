#!/usr/bin/env python3
"""Per-column moves of the dsel-probe designs: model (hcost, colcost) vs realized (@ops labels).

Usage: colfix.py LIST [--seeds A-B]   (LIST as for variance.py)

For every (salt, seed) of the seed range: the model's hole cost per handle h_c (hcost of the design
annealing, recomputed from the saved design state) and the realized moves per request of the papers
of column c by label (fix / dig / fdig / ...; @paper col and @ops of the err files, all order
sequences). Prints the within-case correlation of the per-column realized fix moves with the
per-handle model, and how much of the design effect each column depth range carries.
Writes LIST.colfix.json.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")
K = 192
HOLE_WEIGHT = 0.38
RESET_STRENGTH = 2.0


def barcode_hash_of_input(seed):
    text = Path(f"/home/sato/ahc074/tools/in/{seed:04d}.txt").read_text().split("\n")
    _, _, p, _ = map(int, text[0].split())
    h = 0xCBF29CE484222325
    for s in text[1:1 + p]:
        a = int(s.strip()[::-1], 2)
        for byte in range(8):
            h = ((h ^ (a >> (8 * byte) & 255)) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def load_design(path):
    words = {}
    lines = path.read_text().split("\n")
    for line in lines:
        if line.startswith("stderr"):
            break
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        if key in ("permutation", "A", "edge", "polarity", "papers", "columns", "ded", "handle"):
            words[key] = [int(x) for x in parts[2:]]
        else:
            words[key] = parts[1] if len(parts) > 1 else None
    return words


def model_holes(d):
    """hcost per handle (moves summed over the 256 targets) of the saved design."""
    H = int(d["H"])
    A, columns, ded, handle = d["A"], d["columns"], d["ded"], d["handle"]
    partner = {}
    by_paper = defaultdict(list)
    for t, k in enumerate(ded):
        by_paper[k].append(t)
    for k, ts in by_paper.items():
        if len(ts) == 2:
            partner[ts[0]], partner[ts[1]] = ts[1], ts[0]
    hn = [[0, 0] for _ in range(H)]
    nt = [0] * H
    for t in range(256):
        c = columns[ded[t]]
        nt[c] += 1
        for j in range(H):
            bit = A[t] >> handle[j] & 1
            hole = j > c or (t in partner and (A[partner[t]] >> handle[j] & 1) != bit)
            if hole:
                hn[j][bit] += 1
    cost = []
    for j in range(H):
        x, y, r = hn[j][0], hn[j][1], RESET_STRENGTH * nt[j]
        cost.append(4 * HOLE_WEIGHT * (x * y + .5 * r * min(x, y)) / max(1., x + y + r))
    return cost, hn, nt


def parse_err(path):
    col, labels = None, {}
    for line in path.read_text().splitlines():
        if line.startswith("@paper col = "):
            col = [(-1 if v == "-" else int(v)) for v in line[len("@paper col = "):].split()]
        elif line.startswith("@ops "):
            head, rest = line[5:].split(" =", 1)
            toks = []
            for tok in rest.split():
                if "*" in tok:
                    name, n = tok.split("*")
                    toks += [name] * int(n)
                else:
                    toks.append(tok)
            labels[int(head)] = toks
    return col, labels


def parse_out(path):
    lines = path.read_text().split("\n")
    i, reqs = K, []
    while i < len(lines) and lines[i].strip():
        n = int(lines[i])
        reqs.append([int(lines[i + 1 + t].split()[0]) for t in range(n)])
        i += 1 + n
    return reqs


def main():
    lst = Path(sys.argv[1])
    lo, hi = 0, 10 ** 9
    if "--seeds" in sys.argv:
        lo, hi = map(int, sys.argv[sys.argv.index("--seeds") + 1].split("-"))
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    result = {}
    for salt, design_run, orders_run in rows:
        run = RUNS / orders_run
        meta = json.loads((run / "meta.json").read_text())
        n_orders = meta.get("design_from", {}).get("orders", 1)
        for c in json.loads((run / "result.json").read_text())["cases"]:
            seed = c["seed"]
            if not lo <= seed < hi:
                continue
            d = load_design(RUNS / design_run / "design" / f"{barcode_hash_of_input(seed)}.txt")
            H = int(d["H"])
            cost, hn, nt = model_holes(d)
            per = defaultdict(lambda: [0.0] * H)  # label -> moves per column
            nreq = 0
            for j in range(n_orders):
                base = run if j == 0 else run / "orders" / str(j)
                col, labels = parse_err(base / "err" / f"{seed:04d}.txt")
                reqs = parse_out(base / "out" / f"{seed:04d}.txt")
                for r, papers in enumerate(reqs):
                    lab = labels.get(r, [])
                    if len(lab) != len(papers):
                        continue
                    nreq += 1
                    for k, l in zip(papers, lab):
                        cc = col[k]
                        if cc >= 0:
                            per[l][cc] += 1
            result[f"{salt}:{seed}"] = {
                "model_h": [x / 256 for x in cost], "hn": hn, "nt": nt,
                "real": {l: [x / nreq for x in v] for l, v in per.items()},
                "logscore": 100 * float(np.mean([math.log(x) for x in (c.get("order_scores") or [c["score"]])])),
            }
    out = lst.with_suffix(".colfix.json") if "--out" not in sys.argv else Path(sys.argv[sys.argv.index("--out") + 1])
    out.write_text(json.dumps(result))
    salts = sorted({k.split(":")[0] for k in result}, key=int)
    seeds = sorted({int(k.split(":")[1]) for k in result})
    H = len(result[f"{salts[0]}:{seeds[0]}"]["model_h"])
    # model hole cost per handle vs realized fix moves of the column (pooled over designs, per column)
    print(f"{len(seeds)} cases x {len(salts)} designs (H = {H})")
    print(f"{'col':>4s} {'model':>8s} {'fix':>8s} {'fix+fill':>9s} {'r(model,fix) within case':>25s} {'sd fix within':>14s} {'r(fix, logscore)':>17s}")
    y = np.array([[result[f"{s}:{c}"]["logscore"] for s in salts] for c in seeds])
    yd = y - y.mean(axis=1, keepdims=True)
    for j in range(H):
        m = np.array([[result[f"{s}:{c}"]["model_h"][j] for s in salts] for c in seeds])
        f = np.array([[result[f"{s}:{c}"]["real"].get("fix", [0] * H)[j] for s in salts] for c in seeds])
        md, fd = m - m.mean(axis=1, keepdims=True), f - f.mean(axis=1, keepdims=True)
        r = (md * fd).sum() / math.sqrt((md ** 2).sum() * (fd ** 2).sum() + 1e-300)
        r2 = (fd * yd).sum() / math.sqrt((fd ** 2).sum() * (yd ** 2).sum() + 1e-300)
        print(f"{j:4d} {m.mean():8.4f} {f.mean():8.4f} {'':9s} {r:25.3f} {fd.std():14.4f} {r2:17.3f}")


if __name__ == "__main__":
    main()
