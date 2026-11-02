#!/usr/bin/env python3
"""Fixed-design simulation of baseline vs the generic-layer MDP.

This research harness does not run the contest tester and is not a 2-second
submission benchmark. The normal paired evaluation remains pahcer_run.py.
It generates scratch copies, fixes all design iteration budgets, disables the
helper/MDP preprocessing deadlines, and executes the existing SIM_HARNESS path.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time


REPO = Path(__file__).resolve().parents[2]
PARAMETERS = ("MAP_ITERS", "GOPT_STEPS", "ANNEAL_ITERS", "CLIMB_ITERS", "SIM_SEQS")
DIAGNOSTICS = ("GENERIC_MDP_ITERS", "GENERIC_MDP_SCORE", "GENERIC_MDP_PROBE")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seed_list(spec: str) -> list[int]:
    seeds: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            first, end = map(int, part.split("-"))
            seeds.extend(range(first, end))
        else:
            seeds.append(int(part))
    return sorted(set(seeds))


def prepare_source(source: str, *, mdp: bool) -> tuple[str, list[str]]:
    old = "constexpr double kHelperGiveUp = 1.55;"
    if source.count(old) != 1:
        raise ValueError("Expected the reviewed helper deadline exactly once")
    source = source.replace(old, "constexpr double kHelperGiveUp = 1e9;")
    edits = ["kHelperGiveUp 1.55 -> 1e9"]
    if mdp:
        old = "if (it > 0 && elapsed_sec() > 1.58) break;"
        if source.count(old) != 1:
            raise ValueError("Expected the reviewed MDP deadline exactly once")
        source = source.replace(old, "if (it > 0 && elapsed_sec() > 1e9) break;")
        edits.append("MDP preprocessing deadline 1.58 -> 1e9")
    marker = "#ifdef SIM_HARNESS\n    // Experiments only"
    if source.count(marker) != 1:
        raise ValueError("Expected the existing SIM_HARNESS entry exactly once")
    diagnostic = """#ifdef SIM_HARNESS
    std::cerr.precision(12);
    u64 design_fingerprint = 1469598103934665603ULL;
    auto fingerprint_word = [&](u64 x) {
        for (int byte = 0; byte < 8; ++byte) {
            design_fingerprint ^= (x >> (8 * byte)) & 255;
            design_fingerprint *= 1099511628211ULL;
        }
    };
    for (const auto& pp : papers) {
        fingerprint_word(pp.opaque);
        fingerprint_word(pp.black);
    }
    for (int x : columns) fingerprint_word(u64(x));
    for (int x : ded) fingerprint_word(u64(x));
    for (int x : solver.handle) fingerprint_word(u64(x));
    for (int x : permutation) fingerprint_word(u64(x));
    std::cerr << "sim_design_fingerprint = " << design_fingerprint << '\\n';
    // Experiments only"""
    source = source.replace(marker, diagnostic)
    edits.append("Emit 64-bit design fingerprint and 12-digit simulation means")
    return source, edits


def parse_metrics(stderr: str) -> dict[str, float | int | str]:
    result: dict[str, float | int | str] = {}
    for line in stderr.splitlines():
        match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(\S+)", line)
        if match:
            name, value = match.groups()
            if name == "sim_design_fingerprint":
                result[name] = value
            else:
                try:
                    result[name] = float(value)
                except ValueError:
                    pass
    return result


def summarize(rows: list[dict]) -> dict:
    valid = [row for row in rows if row.get("error") is None]
    if not valid:
        return {"count": 0, "errors": len(rows)}
    ratios = [math.log(row["mdp"]["sim_moves"] / row["baseline"]["sim_moves"]) for row in valid]
    deltas = [row["mdp"]["sim_moves"] - row["baseline"]["sim_moves"] for row in valid]
    out = {
        "count": len(valid),
        "errors": len(rows) - len(valid),
        "mean_log_ratio_percent": statistics.mean(ratios) * 100,
        "standard_error_percent": statistics.stdev(ratios) / math.sqrt(len(valid)) * 100 if len(valid) > 1 else None,
        "mean_delta_moves_per_request": statistics.mean(deltas),
        "wins_ties_losses": [sum(d < -1e-9 for d in deltas), sum(abs(d) <= 1e-9 for d in deltas), sum(d > 1e-9 for d in deltas)],
        "baseline_mean_moves_per_request": statistics.mean(row["baseline"]["sim_moves"] for row in valid),
        "mdp_mean_moves_per_request": statistics.mean(row["mdp"]["sim_moves"] for row in valid),
    }
    if all("mdp_model_myopic" in row["mdp"] and "mdp_model_policy" in row["mdp"] for row in valid):
        old = statistics.mean(row["mdp"]["mdp_model_myopic"] for row in valid)
        new = statistics.mean(row["mdp"]["mdp_model_policy"] for row in valid)
        out["isolated_generic_model"] = {
            "myopic_moves_per_request": old,
            "mdp_moves_per_request": new,
            "delta_moves_per_request": new - old,
            "fraction_of_total_baseline_percent": (new - old) / out["baseline_mean_moves_per_request"] * 100,
            "note": "iid embedded model; excludes helper interactions and the no-repeat rule",
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0-32", help="End-exclusive ranges, or comma separated seeds")
    parser.add_argument("--input-dir", type=Path, default=REPO / "tools/in")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--map-iters", type=int, default=200000)
    parser.add_argument("--gopt-steps", type=int, default=60000)
    parser.add_argument("--anneal-iters", type=int, default=4000000)
    parser.add_argument("--climb-iters", type=int, default=20000)
    parser.add_argument("--sim-seqs", type=int, default=8)
    parser.add_argument("--mdp-iters", type=int, default=16)
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    seeds = seed_list(args.seeds)
    if not seeds or min(args.workers, args.map_iters, args.gopt_steps, args.anneal_iters, args.climb_iters, args.sim_seqs, args.mdp_iters) <= 0:
        parser.error("All counts must be positive and at least one seed is required")
    output = (args.output or REPO / "runs" / ("chatgpt-transition-fixed-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "src").mkdir()
    (output / "bin").mkdir()
    (output / "logs").mkdir()
    budgets = dict(zip(PARAMETERS, map(str, (args.map_iters, args.gopt_steps, args.anneal_iters, args.climb_iters, args.sim_seqs))))
    metadata = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "fixed-design untimed simulation, not a contest time-limit benchmark",
        "seeds": seeds,
        "workers": args.workers,
        "environment": budgets,
        "request_rng": "mt19937_64(1000003 * (sequence_index+1)); no repeated consecutive item",
        "mdp_iterations": args.mdp_iters,
        "compiler": subprocess.check_output([args.compiler, "--version"], text=True).splitlines()[0],
        "sources": {},
    }
    binaries: dict[str, Path] = {}
    for name, path in (("baseline", REPO / "solutions/imp-combo/main.cpp"), ("mdp", REPO / "solutions/chatgpt-transition/main.cpp")):
        original = path.read_bytes()
        transformed, edits = prepare_source(original.decode(), mdp=name == "mdp")
        source = output / "src" / f"{name}.cpp"
        source.write_text(transformed)
        binary = output / "bin" / name
        command = [args.compiler, "-std=c++23", "-O2", "-DCLOCK_SCALE=1.1", "-DSIM_HARNESS", str(source), "-o", str(binary)]
        print(f"Compiling {name}", flush=True)
        subprocess.run(command, check=True)
        binaries[name] = binary
        metadata["sources"][name] = {
            "original_path": str(path.relative_to(REPO)),
            "original_sha256": sha256(original),
            "generated_sha256": sha256(source.read_bytes()),
            "edits": edits,
            "compile_command": command,
        }
    (output / "meta.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    def run_seed(seed: int) -> dict:
        input_file = args.input_dir / f"{seed:04d}.txt"
        data = input_file.read_bytes()
        row = {"seed": seed, "input_sha256": sha256(data), "error": None}
        variants = ("baseline", "mdp") if seed % 2 == 0 else ("mdp", "baseline")
        for name in variants:
            env = os.environ.copy()
            for key in PARAMETERS + DIAGNOSTICS:
                env.pop(key, None)
            env.update(budgets)
            if name == "mdp":
                env["GENERIC_MDP_ITERS"] = str(args.mdp_iters)
                env["GENERIC_MDP_PROBE"] = "1"
            started = time.monotonic()
            try:
                proc = subprocess.run([str(binaries[name])], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                row["error"] = f"{name} timed out after {args.timeout}s"
                return row
            stderr = proc.stderr.decode(errors="replace")
            (output / "logs" / f"{seed:04d}-{name}.stderr.txt").write_text(stderr)
            metrics = parse_metrics(stderr)
            metrics["process_wall_sec"] = time.monotonic() - started
            row[name] = metrics
            if proc.returncode or "sim_moves" not in metrics or metrics.get("sim_wrong") != 0 or proc.stdout:
                row["error"] = f"{name}: returncode={proc.returncode}, sim_wrong={metrics.get('sim_wrong')}, stdout_bytes={len(proc.stdout)}"
                return row
        if row["baseline"].get("sim_design_fingerprint") != row["mdp"].get("sim_design_fingerprint"):
            row["error"] = "Fixed-design fingerprints differ; comparison invalid"
        return row

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(run_seed, seed): seed for seed in seeds}
        for future in concurrent.futures.as_completed(pending):
            try:
                row = future.result()
            except Exception as exc:
                row = {"seed": pending[future], "error": repr(exc)}
            rows.append(row)
            rows.sort(key=lambda row: row["seed"])
            (output / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
            print(f"{len(rows)}/{len(seeds)} seed={row['seed']} error={row.get('error')}", flush=True)
    summary = summarize(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), **summary}, indent=2, ensure_ascii=False), flush=True)
    if summary.get("errors"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
