#!/usr/bin/env python3
"""Inspect actual printed nonlinear gates without running any solution again.

For each nonlinear window, replace just that window by each of the 30 possible
pair comparisons, while keeping every other window fixed. Count how many of the
actual paired dedicated sheets remain usable for both products. This distinguishes
an arbitrary gate that is essential to the chosen recipes from an equivalent
ordinary comparison. It is a representability diagnostic, not a score estimate.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay

PERMS = list(itertools.permutations(range(6)))
FULL = (1 << 720) - 1
LINEAR = []
for white in range(6):
    for black in range(6):
        if white == black:
            continue
        ones = sum(1 << s for s, p in enumerate(PERMS) if p.index(black) < p.index(white))
        LINEAR.append((white, black, (FULL ^ ones, ones)))


def inspect(run: Path, seed: int) -> list[dict]:
    inp = replay.load_input(seed)
    text = (run / "out" / f"{seed:04d}.txt").read_text()
    rows = text.splitlines()[:192]
    papers = [(replay.mask(s, "0") | replay.mask(s, "1"), replay.mask(s, "1")) for s in rows]
    gm = 0
    for opq, _ in papers[:6]:
        gm |= opq
    pairs = []
    ambiguous = 0
    for opq, black in papers[6:]:
        matches = [u for u, a in enumerate(inp.target) if not ((a ^ black) & opq)]
        if len(matches) == 2:
            pairs.append(tuple(matches))
        elif len(matches) != 1:
            ambiguous += 1
    displays = []
    for order in PERMS:
        color = covered = 0
        for k in order:
            opq, black = papers[k]
            color |= black & ~covered
            covered |= opq
        displays.append(color)
    result = []
    for j in range(64):
        support = [k for k in range(6) if papers[k][0] >> j & 1]
        if len(support) <= 2:
            continue
        can = [0] * len(LINEAR)
        for u, v in pairs:
            a, b = inp.target[u], inp.target[v]
            holes = (a ^ b) & gm
            if not (holes >> j & 1):
                for t in range(len(can)):
                    can[t] += 1
                continue
            other = holes & ~(1 << j)
            fu = sum(1 << s for s, x in enumerate(displays) if not ((x ^ a) & other))
            fv = sum(1 << s for s, x in enumerate(displays) if not ((x ^ b) & other))
            for t, (_, _, masks) in enumerate(LINEAR):
                can[t] += bool(fu & masks[a >> j & 1]) and bool(fv & masks[b >> j & 1])
        best = max(range(len(can)), key=can.__getitem__)
        result.append({
            "seed": seed, "window": j, "gate": "".join(rows[k][j] for k in range(6)),
            "inferred_pairs": len(pairs), "ambiguous_papers": ambiguous,
            "best_linear_white": LINEAR[best][0], "best_linear_black": LINEAR[best][1],
            "best_linear_retained_pairs": can[best], "minimum_recipes_lost": len(pairs) - can[best],
        })
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("run")
    p.add_argument("--csv", type=Path)
    args = p.parse_args()
    run = replay.resolve_run(args.run)
    cases = json.loads((run / "result.json").read_text())["cases"]
    rows = [r for case in cases if case["score"] > 0 for r in inspect(run, case["seed"])]
    if args.csv:
        with args.csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({
        "run": run.name, "cases": len(cases), "nonlinear_windows": len(rows),
        "ambiguous_paper_cases": len({r["seed"] for r in rows if r["ambiguous_papers"]}),
        "essential_windows": sum(r["minimum_recipes_lost"] > 0 for r in rows),
        "mean_minimum_recipes_lost_per_window": sum(r["minimum_recipes_lost"] for r in rows) / max(1, len(rows)),
        "max_minimum_recipes_lost": max((r["minimum_recipes_lost"] for r in rows), default=0),
    }, indent=2))


if __name__ == "__main__":
    main()
