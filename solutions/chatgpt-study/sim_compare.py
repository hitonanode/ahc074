#!/usr/bin/env python3
"""Compare complete solver policies on common simulated requests without a query deadline.

This is a research experiment, not a contest time-limit benchmark. Normal paired
interactive measurements must also be made with run_compare.py. Source changes
are limited to disabling the helper-table initialization deadline in scratch
copies and enabling the baseline's existing SIM_HARNESS. Each design sees the
same request sequences; none is used to choose or improve the design.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("mdp_probe", ROOT / "solutions/chatgpt-transition/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solutions", nargs="+", required=True, help="Baseline first, solution directories")
    parser.add_argument("--seeds", default="0-32")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--map-iters", type=int, default=200000, help="0 retains the common timed map budget")
    parser.add_argument("--gopt-steps", type=int, default=60000, help="0 retains the common timed final map budget")
    parser.add_argument("--anneal-iters", type=int, default=4000000, help="0 retains the submission's timed annealing budget")
    parser.add_argument("--climb-iters", type=int, default=20000, help="0 retains the submission's timed filler climb budget")
    parser.add_argument("--sim-seqs", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1 or args.sim_seqs < 1 or min(args.map_iters, args.gopt_steps, args.anneal_iters, args.climb_iters) < 0:
        parser.error("Worker/simulation counts must be positive; iteration budgets must be nonnegative")
    seeds = probe.seed_list(args.seeds)
    paths = [(ROOT / p).resolve() / "main.cpp" for p in args.solutions]
    names = [p.parent.name for p in paths]
    if len(set(names)) != len(names):
        parser.error("Solution names must be distinct")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for sub in ("src", "bin", "logs"):
        (output / sub).mkdir()
    budgets = dict(zip(probe.PARAMETERS, map(str, (args.map_iters, args.gopt_steps, args.anneal_iters, args.climb_iters, args.sim_seqs))))
    meta = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "common-request simulation; no query deadline; not a 2-second result",
        "baseline_remote_commit": "dee23c8fce0eba04e513478629402f20b843e9f0",
        "seeds": seeds, "workers": args.workers, "environment": budgets,
        "request_generator": "mt19937_64(1000003 * (sequence_index+1)); consecutive duplicates excluded",
        "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
        "sources": {},
    }
    lock = open(ROOT / "runs/.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX)
    binaries = {}
    for name, path in zip(names, paths):
        original = path.read_bytes()
        source, edits = probe.prepare_source(original.decode(), mdp=name == "chatgpt-transition")
        diagnostic_marker = "    u64 design_fingerprint = 1469598103934665603ULL;"
        if source.count(diagnostic_marker) != 1:
            raise ValueError("Missing unique simulation diagnostic marker")
        model_diagnostic = """    // Research-only reconstruction of the design model, after design is fixed.
    des->rebuild();
    double model_retrieval = 0, model_holes = 0, model_generic = 0, dedicated_holes = 0;
    for (int c = 0; c < des->H; ++c) {
        model_retrieval += des->colcost(c);
        model_holes += des->hcost(c);
    }
    for (const auto& unit : des->unit) model_generic += des->gc(unit);
    for (int u = 0; u < P; ++u)
        dedicated_holes += __builtin_popcountll(solver.hmask & ~papers[ded[u]].opaque);
    std::cerr << "model_retrieval = " << model_retrieval / P
              << "\\nmodel_holes = " << model_holes / P
              << "\\nmodel_generic = " << model_generic / P
              << "\\nmean_dedicated_handle_holes = " << dedicated_holes / P << '\\n';
"""
        source = source.replace(diagnostic_marker, model_diagnostic + diagnostic_marker)
        edits.append("Emit decomposed design-model costs and mean handle-hole count")
        dest = output / "src" / f"{name}.cpp"
        dest.write_text(source)
        binary = output / "bin" / name
        command = ["g++", "-std=c++23", "-O2", "-DCLOCK_SCALE=1.1", "-DSIM_HARNESS", str(dest), "-o", str(binary)]
        print(f"Compiling {name}", flush=True)
        subprocess.run(command, check=True)
        binaries[name] = binary
        meta["sources"][name] = {"path": str(path.relative_to(ROOT)), "sha256": probe.sha256(original),
                                  "generated_sha256": probe.sha256(dest.read_bytes()), "edits": edits,
                                  "compile_command": command}
    (output / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    def run(seed):
        data = (ROOT / "tools/in" / f"{seed:04d}.txt").read_bytes()
        row = {"seed": seed, "input_sha256": hashlib.sha256(data).hexdigest(), "error": None}
        order = names[seed % len(names):] + names[:seed % len(names)]
        for name in order:
            env = os.environ.copy()
            for key in (*probe.PARAMETERS, *probe.DIAGNOSTICS, "MATCH_REPAIR_PASSES"):
                env.pop(key, None)
            env.update(budgets)
            started = time.monotonic()
            proc = subprocess.run([str(binaries[name])], input=data, capture_output=True, env=env, timeout=180)
            stderr = proc.stderr.decode(errors="replace")
            (output / "logs" / f"{seed:04d}-{name}.txt").write_text(stderr)
            m = probe.parse_metrics(stderr)
            m["process_wall_sec"] = time.monotonic() - started
            row[name] = m
            if proc.returncode or proc.stdout or "sim_moves" not in m or m.get("sim_wrong") != 0:
                row["error"] = f"{name}: exit={proc.returncode}, stdout={len(proc.stdout)}, sim_wrong={m.get('sim_wrong')}"
                break
        return row

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, s): s for s in seeds}
        for future in concurrent.futures.as_completed(futures):
            try:
                row = future.result()
            except Exception as exc:
                row = {"seed": futures[future], "error": repr(exc)}
            rows.append(row)
            rows.sort(key=lambda r: r["seed"])
            (output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(f"{len(rows)}/{len(seeds)} seed={row['seed']} error={row['error']}", flush=True)
    valid = [r for r in rows if r["error"] is None]
    summary = {"cases": len(rows), "valid_cases": len(valid), "errors": len(rows)-len(valid),
               "sequences_per_case": args.sim_seqs, "solutions": []}
    for name in names:
        logs = [math.log(r[name]["sim_moves"] / r[names[0]]["sim_moves"]) * 100 for r in valid]
        delta = [r[name]["sim_moves"] - r[names[0]]["sim_moves"] for r in valid]
        metrics = {}
        if valid:
            for key in valid[0][name]:
                vals = [r[name][key] for r in valid if isinstance(r[name].get(key), (int, float))]
                if len(vals) == len(valid):
                    metrics[key] = statistics.mean(vals)
        summary["solutions"].append({"name": name,
            "mean_moves_per_request": statistics.mean(r[name]["sim_moves"] for r in valid) if valid else None,
            "mean_log_ratio_percent": statistics.mean(logs) if logs else None,
            "standard_error_percent": statistics.stdev(logs)/math.sqrt(len(logs)) if len(logs)>1 else None,
            "wins_ties_losses": [sum(d < -1e-9 for d in delta), sum(abs(d) <= 1e-9 for d in delta), sum(d > 1e-9 for d in delta)],
            "mean_metrics": metrics})
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
