#!/usr/bin/env python3
"""Export paired AHC074 measurements with checked inputs and source provenance.

Example:
  python3 solutions/chatgpt-study/summarize.py --runs RUN0 RUN1 RUN2 \
      --manifest tools/in/chatgpt_manifest.json --out solutions/chatgpt-study/results/pilot --verify

All runs must contain the same input indices. A manifest captures the actual input
bytes; it is checked before computing or trusting metrics. --verify additionally
replays every move with the independent scripts/replay.py implementation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTE_BASE = "dee23c8fce0eba04e513478629402f20b843e9f0"
sys.path.insert(0, str(ROOT / "scripts"))
import replay  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo) if lo != hi else xs[lo]


def average(values):
    return statistics.fmean(values) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True, help="baseline first")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--remote-base", default=REMOTE_BASE)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    run_dirs = [replay.resolve_run(s) for s in args.runs]
    results = [json.loads((p / "result.json").read_text()) for p in run_dirs]
    metas = [json.loads((p / "meta.json").read_text()) for p in run_dirs]
    if any(m.get("status") != "ok" for m in metas):
        raise SystemExit("All runs must have completed successfully")
    case_maps = [{c["seed"]: c for c in r["cases"]} for r in results]
    indices = sorted(case_maps[0])
    if any(set(cases) != set(indices) for cases in case_maps):
        raise SystemExit("Runs contain different input indices; compare a common completed set")
    source_manifest = json.loads(args.manifest.read_text())
    inputs = {c["index"]: c for c in source_manifest["cases"]}
    used_inputs = []
    for i in indices:
        if i not in inputs:
            raise SystemExit(f"Input index {i} missing from supplied manifest")
        record = inputs[i]
        if sha256(ROOT / "tools" / "in" / f"{i:04d}.txt") != record["sha256"]:
            raise SystemExit(f"Input index {i}: current bytes do not match the supplied manifest")
        used_inputs.append(record)

    metrics_list = []
    verification = []
    for run_dir, case_map in zip(run_dirs, case_maps):
        metrics = replay.run_metrics(run_dir)
        metrics_list.append(metrics)
        checked = 0
        failures = []
        if args.verify:
            for i in indices:
                inp = replay.load_input(i)
                out = replay.parse_output(inp, (run_dir / "out" / f"{i:04d}.txt").read_text())
                if out.error:
                    failures.append({"index": i, "error": out.error})
                    continue
                game = replay.Game(inp, out.designs)
                try:
                    for r, ops in enumerate(out.queries):
                        for paper, depth in ops:
                            game.move(paper, depth)
                        game.finish(r)
                    if game.score() != case_map[i]["score"]:
                        failures.append({"index": i, "error": "Score mismatch",
                                         "replay_score": game.score(), "tester_score": case_map[i]["score"]})
                    else:
                        checked += 1
                except (replay.InvalidMove, ValueError) as exc:
                    failures.append({"index": i, "error": str(exc)})
        verification.append({"run_id": run_dir.name, "visibility_replayed": args.verify,
                             "checked": checked, "failures": failures})
        if failures:
            raise SystemExit(f"Independent replay found errors: {verification[-1]}")

    rows = []
    summaries = []
    base = case_maps[0]
    for run_dir, cases, metrics, meta in zip(run_dirs, case_maps, metrics_list, metas):
        logs = []
        score_differences = []
        for i in indices:
            case, bcase, metric = cases[i], base[i], metrics[i]
            stderr = metric.get("stderr", {})
            valid_pair = case["score"] > 0 and bcase["score"] > 0
            delta = case["score"] - bcase["score"] if valid_pair else None
            log_ratio = math.log(case["score"] / bcase["score"]) if valid_pair else None
            if valid_pair:
                logs.append(log_ratio)
                score_differences.append(delta)
            row = {
                "run_id": run_dir.name, "solution": Path(meta["source"]["path"]).name,
                "input_index": i, "rng_seed": inputs[i].get("rng_seed"),
                "input_sha256": inputs[i]["sha256"], "score": case["score"],
                "E": metric.get("E"), "T": metric.get("T"),
                "moves_per_request": metric.get("ops_mean"),
                "execution_seconds": case["execution_time"],
                "baseline_score": bcase["score"], "score_difference": delta,
                "log_ratio_percent": 100 * log_ratio if log_ratio is not None else None,
                "fast_requests": stderr.get("fast_requests", 0),
                "plan_failures": stderr.get("plan_failures", 0),
                "emergency_design": stderr.get("emergency_design", 0),
                "self_wrong": stderr.get("self_wrong", 0),
                "map_iters": stderr.get("map_iters"),
                "anneal_iters": stderr.get("anneal_iters"),
                "helper_end_seconds": stderr.get("helper_end_sec"),
                "request_seconds": stderr.get("req_sec"),
                "solver_end_seconds": stderr.get("end_sec"),
                "error_message": case.get("error_message", ""),
            }
            rows.append(row)
        valid = [cases[i] for i in indices if cases[i]["score"] > 0]
        valid_metrics = [metrics[c["seed"]] for c in valid]
        times = [cases[i]["execution_time"] for i in indices]
        se = statistics.stdev(logs) / math.sqrt(len(logs)) if len(logs) > 1 else None
        mean_log = average(logs)
        summaries.append({
            "run_id": run_dir.name, "solution": Path(meta["source"]["path"]).name,
            "cases": len(indices), "valid_pairs": len(logs),
            "WA": len(indices) - len(valid),
            "WA_indices": [i for i in indices if cases[i]["score"] == 0],
            "mean_score": average([c["score"] for c in valid]),
            "mean_E": average([m["E"] for m in valid_metrics]),
            "mean_T": average([m["T"] for m in valid_metrics]),
            "moves_per_request": average([m["ops_mean"] for m in valid_metrics]),
            "mean_log_ratio_percent": 100 * mean_log if mean_log is not None else None,
            "standard_error_percent": 100 * se if se is not None else None,
            "approx_95pct_CI_percent": [100 * (mean_log - 1.96 * se), 100 * (mean_log + 1.96 * se)]
                                      if se is not None else None,
            "geometric_score_change_percent": 100 * math.expm1(mean_log) if mean_log is not None else None,
            "mean_paired_score_difference": average(score_differences),
            "better_equal_worse": [sum(x < 0 for x in logs), sum(x == 0 for x in logs), sum(x > 0 for x in logs)],
            "time_seconds": {"mean": average(times), "p50": quantile(times, 0.50),
                             "p95": quantile(times, 0.95), "max": max(times)},
            "over_2_seconds": sum(t > 2.0 for t in times),
            "mean_fast_requests": average([m.get("stderr", {}).get("fast_requests", 0) for m in valid_metrics]),
            "emergency_design_cases": sum(m.get("stderr", {}).get("emergency_design", 0) > 0 for m in valid_metrics),
            "mean_stderr": {key: average([m["stderr"][key] for m in valid_metrics if key in m.get("stderr", {})])
                            for key in sorted({key for m in valid_metrics for key in m.get("stderr", {})})},
            "source_sha256": sha256(run_dir / "src" / "main.cpp"),
            "compile_command": meta["compile_command"], "compiler": meta.get("compiler"),
            "local_source_snapshot": meta["source"].get("git"),
            "comment": meta.get("comment"),
            # The repository preserves the first comparison table when a run
            # is extended. The statistics above always cover all current cases.
            "initial_runner_compare_metadata": meta.get("compare"),
            "runner_extensions": meta.get("extensions", []),
        })
    args.out.mkdir(parents=True, exist_ok=True)
    document = {
        "remote_repository": "hitonanode/ahc074", "remote_base_commit": args.remote_base,
        "local_git_commit_is_an_artificial_materialization": True,
        "baseline_run": run_dirs[0].name,
        "generator": source_manifest["generator"], "official_rust_seeds": False,
        "input_indices": indices, "source_manifest_sha256": sha256(args.manifest),
        "tester": {"kind": "C++ ASCII-protocol port of repository official Rust tester",
                   "source_sha256": sha256(ROOT / "solutions" / "chatgpt-study" / "tester.cpp"),
                   "binary_sha256": sha256(ROOT / "tools" / "target" / "release" / "tester")},
        "comparison": "100 * mean(log(candidate_score / baseline_score)); lower is better",
        "standard_error": "Sample standard deviation of paired log ratios divided by sqrt(case count)",
        "timing_note": "Local wall time includes tester and IPC; this is not an AtCoder runtime certification",
        "summaries": summaries, "independent_replay": verification,
    }
    (args.out / "summary.json").write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    (args.out / "inputs.json").write_text(json.dumps({"generator": source_manifest["generator"],
        "official_rust_seeds": False, "cases": used_inputs}, indent=2) + "\n")
    with (args.out / "per_case.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for summary in summaries:
        print(json.dumps({key: summary[key] for key in ("run_id", "cases", "WA", "mean_score", "mean_E",
            "moves_per_request", "mean_log_ratio_percent", "standard_error_percent", "better_equal_worse",
            "time_seconds", "over_2_seconds", "mean_fast_requests")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
