#!/usr/bin/env python3
"""Compact paired score and time statistics from saved runs; never reruns a solver."""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay


def mean_se(values):
    return {"n": len(values), "mean": statistics.fmean(values) if values else None,
            "se": statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None}


def f(value, precision=4):
    return "N/A" if value is None else f"{value:.{precision}f}"


def mse(value, scale=1, precision=4):
    return f"{f(None if value['mean'] is None else value['mean'] * scale, precision)} ± " \
           f"{f(None if value['se'] is None else value['se'] * scale, precision)}"


def load_run(arg):
    path = replay.resolve_run(arg)
    cases = replay.run_cases(path)
    metrics = replay.run_metrics(path, processes=1)
    valid = [seed for seed in cases if cases[seed]["score"] > 0]
    times = [c["execution_time"] for c in cases.values()]
    stats = {}
    for seed in valid:
        for key, value in metrics[seed].get("stderr", {}).items():
            stats.setdefault(key, []).append(value)
    requests = sum(metrics[s]["requests"] for s in valid)
    moves = sum(metrics[s]["T"] for s in valid)
    errors = sum(metrics[s]["E"] for s in valid)
    fast_seeds = [s for s in valid if "fast_requests" in metrics[s].get("stderr", {})]
    fast_den = sum(metrics[s]["requests"] for s in fast_seeds)
    fast_num = sum(metrics[s]["stderr"]["fast_requests"] for s in fast_seeds)
    report = {
        "run_id": path.name, "path": str(path), "cases": len(cases), "valid": len(valid),
        "wa_seeds": [s for s in cases if cases[s]["score"] <= 0],
        "mean_score": statistics.fmean(cases[s]["score"] for s in valid) if valid else None,
        "mean_moves_per_request": moves / requests if requests else None,
        "mean_T": moves / len(valid) if valid else None,
        "mean_E": errors / len(valid) if valid else None,
        "total_E": errors, "total_T": moves, "requests": requests,
        "replay_mismatch": [s for s in cases if metrics[s]["score"] != cases[s]["score"]],
        "wall_sec": {"mean": statistics.fmean(times) if times else None,
                     "p50": replay.percentile(times, 0.5) if times else None,
                     "p95": replay.percentile(times, 0.95) if times else None,
                     "max": max(times) if times else None},
        "over_2s_seeds": [s for s in cases if cases[s]["execution_time"] > 2.0],
        "fast_requests": fast_num, "fast_observed_requests": fast_den,
        "fast_request_fraction": fast_num / fast_den if fast_den else None,
        "emergency_cases": sum(metrics[s].get("stderr", {}).get("emergency_design", 0) > 0 for s in valid),
        "plan_failures": sum(stats.get("plan_failures", [])),
        "stderr_stats": {key: mean_se(values) for key, values in sorted(stats.items())},
    }
    return cases, metrics, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--json", type=Path, help="Save all aggregates as JSON")
    parser.add_argument("--stat", action="append", default=[], help="Additional stderr metric to print")
    args = parser.parse_args()
    base, base_metrics, br = load_run(args.baseline)
    cand, cand_metrics, cr = load_run(args.candidate)
    shared = sorted(base.keys() & cand.keys())
    pairs = [s for s in shared if base[s]["score"] > 0 and cand[s]["score"] > 0]
    diffs = [cand[s]["score"] - base[s]["score"] for s in pairs]
    logs = [math.log(cand[s]["score"] / base[s]["score"]) for s in pairs]
    move_diffs = [cand_metrics[s]["ops_mean"] - base_metrics[s]["ops_mean"] for s in pairs]
    joint = {
        "shared_cases": len(shared), "valid_pairs": len(pairs), "raw_score_difference": mean_se(diffs),
        "log_score_ratio": mean_se(logs), "moves_per_request_difference": mean_se(move_diffs),
        "candidate_win_tie_loss": [sum(x < 0 for x in diffs), sum(x == 0 for x in diffs), sum(x > 0 for x in diffs)],
        "excluded_wa_seeds": sorted(set(shared) - set(pairs)),
        "seed_min": min(pairs) if pairs else None, "seed_max": max(pairs) if pairs else None,
    }
    report = {"baseline": br, "candidate": cr, "paired": joint,
              "notes": ["SE is across paired cases, not across requests.",
                        "WA cases are excluded from score averages and paired differences.",
                        "Cases over 2 seconds remain in score differences and are separately reported.",
                        "execution_time is wrapper wall time; CPU is available only if the evaluator logged it.",
                        "solver end_sec/req_sec are CLOCK_SCALE-adjusted; evaluator *_sec are raw seconds."]}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"Baseline : {br['run_id']}")
    print(f"Candidate: {cr['run_id']}")
    print(f"Paired valid cases: {len(pairs)}/{len(shared)}; candidate win/tie/loss = "
          + "/".join(map(str, joint["candidate_win_tie_loss"])))
    print(f"Candidate - baseline score : {mse(joint['raw_score_difference'], precision=2)} (SE)")
    print(f"Candidate - baseline moves : {mse(joint['moves_per_request_difference'])} / request (SE)")
    print(f"100 * mean log(cand/base)  : {mse(joint['log_score_ratio'], scale=100)} % (SE; negative better)")
    print("Metric                              Baseline       Candidate")
    for label, key, prec in [("Mean moves / request", "mean_moves_per_request", 5),
                             ("Mean score", "mean_score", 2), ("Mean E", "mean_E", 4),
                             ("Total E", "total_E", 0), ("Mean T", "mean_T", 2)]:
        print(f"{label:32s} {f(br[key], prec):>13s} {f(cr[key], prec):>15s}")
    print(f"{'WA / >2s / replay mismatch':32s} "
          f"{len(br['wa_seeds'])}/{len(br['over_2s_seeds'])}/{len(br['replay_mismatch']):<7d} "
          f"{len(cr['wa_seeds'])}/{len(cr['over_2s_seeds'])}/{len(cr['replay_mismatch'])}")
    for metric in ["mean", "p50", "p95", "max"]:
        print(f"{'Wall seconds ' + metric:32s} {f(br['wall_sec'][metric]):>13s} {f(cr['wall_sec'][metric]):>15s}")
    for label, key, prec in [("Fast-mode request fraction", "fast_request_fraction", 5),
                             ("Emergency-design cases", "emergency_cases", 0),
                             ("Total plan failures", "plan_failures", 0)]:
        print(f"{label:32s} {f(br[key], prec):>13s} {f(cr[key], prec):>15s}")
    keys = ["solver_cpu_sec", "tester_cpu_sec", "tester_wall_sec", "end_sec", "req_sec", "map_iters",
            "anneal_iters", "generic_moves", "post_saved", "G", *args.stat]
    for key in dict.fromkeys(keys):
        b = br["stderr_stats"].get(key, {}).get("mean")
        c = cr["stderr_stats"].get(key, {}).get("mean")
        if b is not None or c is not None:
            print(f"{'Mean ' + key:32s} {f(b):>13s} {f(c):>15s}")
    print("WA excluded; >2s retained and counted separately. CPU=raw getrusage; solver clocks are scaled.")


if __name__ == "__main__":
    main()
