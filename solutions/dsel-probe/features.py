#!/usr/bin/env python3
"""Per-design features of the dsel-probe runs, and their relation to the design effect.

Usage: features.py LIST [--labels]   (LIST as for variance.py)

For every (salt, seed): the design's stderr metrics (`name = number` printed by the design, from the
orders run's err/<seed>.txt), and with --labels the moves per request of every @ops label averaged
over the order sequences. Writes LIST.features.json and prints, for every feature, the within-case
correlation with the design effect (the mean log score over the order sequences, demeaned per case)
and the regression slope.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RUNS = Path("/home/sato/ahc074/runs")
METRIC = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*) = (-?[0-9.]+(?:e[-+]?[0-9]+)?)$")
DESIGN_KEYS = None  # all numeric keys before helper_end_sec are design metrics


def parse_err(path, labels):
    metrics, counts, requests = {}, Counter(), 0
    for line in path.read_text().splitlines():
        if line.startswith("@ops "):
            if labels:
                requests += 1
                _, rest = line[5:].split(" =", 1)
                for tok in rest.split():
                    if "*" in tok:
                        name, n = tok.split("*")
                        counts[name] += int(n)
                    else:
                        counts[tok] += 1
            continue
        m = METRIC.match(line.strip())
        if m:
            metrics.setdefault(m.group(1), float(m.group(2)))  # first value: the design's
    return metrics, counts, requests


def main():
    labels = "--labels" in sys.argv
    lst = Path(sys.argv[1])
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    feats = {}
    for salt, design_run, orders_run in rows:
        run = RUNS / orders_run
        meta = json.loads((run / "meta.json").read_text())
        n_orders = meta.get("design_from", {}).get("orders", 1)
        cases = json.loads((run / "result.json").read_text())["cases"]
        for c in cases:
            seed = c["seed"]
            m, cnt, req = parse_err(run / "err" / f"{seed:04d}.txt", labels)
            if labels:
                for j in range(1, n_orders):
                    _, cj, rj = parse_err(run / "orders" / str(j) / "err" / f"{seed:04d}.txt", True)
                    cnt.update(cj)
                    req += rj
                for k, v in cnt.items():
                    m["lbl_" + k] = v / max(req, 1)
            scores = c.get("order_scores") or [c["score"]]
            m["logscore"] = 100 * float(np.mean([math.log(x) for x in scores]))
            feats[f"{salt}:{seed}"] = m
    out = lst.with_suffix(".features.json")
    out.write_text(json.dumps(feats))
    # within-case analysis
    salts = sorted({int(k.split(":")[0]) for k in feats})
    seeds = sorted({int(k.split(":")[1]) for k in feats})
    keys = sorted(set.intersection(*(set(v) for v in feats.values())))
    X = {k: np.array([[feats[f"{s}:{c}"][k] for s in salts] for c in seeds]) for k in keys}
    y = X["logscore"]
    yd = y - y.mean(axis=1, keepdims=True)
    print(f"{len(seeds)} cases x {len(salts)} designs; within-case sd of logscore {yd.std():.3f}%")
    res = []
    for k in keys:
        if k == "logscore":
            continue
        x = X[k]
        xd = x - x.mean(axis=1, keepdims=True)
        if xd.std() < 1e-12:
            continue
        r = float((xd * yd).sum() / math.sqrt((xd ** 2).sum() * (yd ** 2).sum()))
        slope = float((xd * yd).sum() / (xd ** 2).sum())
        res.append((abs(r), k, r, slope, float(xd.std()), float(x.mean())))
    res.sort(reverse=True)
    print(f"{'feature':28s} {'r':>7s} {'slope(%/unit)':>14s} {'within sd':>10s} {'mean':>10s}")
    for _, k, r, slope, sd, mean in res[:60]:
        print(f"{k:28s} {r:+7.3f} {slope:+14.4f} {sd:10.4f} {mean:10.4f}")


if __name__ == "__main__":
    main()
