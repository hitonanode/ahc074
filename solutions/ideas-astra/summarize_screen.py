#!/usr/bin/env python3
"""ia-perf-screen の stderr だけを集計する。ソルバ/テスターは起動しない。"""

import argparse
import json
import math
from pathlib import Path
import statistics


def read_metrics(path):
    values = {}
    for line in path.read_text().splitlines():
        if " = " not in line:
            continue
        key, raw = line.split(" = ", 1)
        try:
            values[key] = float(raw)
        except ValueError:
            pass
    return values


def moments(values):
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "se": statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0,
        "max": max(values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=Path("/home/sato/ahc074/runs"))
    parser.add_argument("--base", default="20261109-092025_dcomp-combo-dual30")
    parser.add_argument("--audit", default="20261109-092025_ia-perf-screen")
    args = parser.parse_args()
    base, audit = args.runs / args.base, args.runs / args.audit
    files = sorted((audit / "err").glob("*.txt"))
    rows = [read_metrics(p) for p in files]
    base_rows = [read_metrics(base / "err" / p.name) for p in files]
    kinds = ("rejected", "checked", "missed", "missed_restores", "gain", "max_gain")
    candidate_summary = []
    for candidate in range(9):
        item = {"candidate": candidate, "mode": "warm" if candidate in (5, 7, 8) else "cold"}
        for kind in kinds:
            values = [row[f"ia_screen_{kind}_{candidate}"] for row in rows]
            item[kind] = {"sum": sum(values), "nonzero_seeds": sum(v != 0 for v in values), **moments(values)}
        candidate_summary.append(item)
    checked = sum(sum(row[f"ia_screen_checked_{i}"] for i in range(9)) for row in rows)
    missed = sum(sum(row[f"ia_screen_missed_{i}"] for i in range(9)) for row in rows)
    gains = {
        "selected_candidate": [row[f'ia_screen_gain_{int(row["dv_chosen"])}'] for row in rows],
        "max_candidate_sum": [max(row[f"ia_screen_gain_{i}"] for i in range(9)) for row in rows],
        "all_candidates_sum": [sum(row[f"ia_screen_gain_{i}"] for i in range(9)) for row in rows],
    }
    time_keys = ("dv_anneal_sec", "dv_finish_sec", "dv_eval_sec", "helper_end_sec", "req_sec", "end_sec")
    paired_ms = {
        key: moments([1000 * (row[key] - ref[key]) for row, ref in zip(rows, base_rows) if key in row and key in ref])
        for key in time_keys
    }
    out_files = list((audit / "out").glob("*.txt"))
    result = {
        "base_run": args.base,
        "audit_run": args.audit,
        "seeds": len(rows),
        "stdout_files": len(out_files),
        "stdout_equal": sum(p.read_bytes() == (base / "out" / p.name).read_bytes() for p in out_files),
        "checked": checked,
        "missed": missed,
        "missed_fraction": missed / checked,
        "seeds_with_missed": sum(any(row[f"ia_screen_missed_{i}"] > 0 for i in range(9)) for row in rows),
        "missed_restores": sum(sum(row[f"ia_screen_missed_restores_{i}"] for i in range(9)) for row in rows),
        "model_gain_moves_per_order": {key: moments(values) for key, values in gains.items()},
        "paired_ms": paired_ms,
        "by_candidate": candidate_summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
