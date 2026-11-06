#!/usr/bin/env python3
"""Reproduce the AHC074 paper-count experiment with the GitHub repository inputs.

This compact GitHub-side runner is independent from the larger original ZIP's
benchmark suite. It preserves the same solver build flags, constants and
paired inputs; results are verified by replay-checker. It does not impose
AtCoder's two-second judge timeout (the study is a counterfactual K sweep).
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
KS = (182, 184, 186, 188, 190, 191, 192, 193, 194, 196, 198, 200, 202)
STRIP_PREFIX = ("F2_", "F3_", "COLMDP", "DESIGN_", "SIM_")
STRIP_NAMES = {
    "MAP_ITERS", "GOPT_STEPS", "ANNEAL_ITERS", "CLIMB_ITERS",
    "ITER_SCALE", "CLOCK_SCALE",
}


def environment():
    return {k: v for k, v in os.environ.items()
            if k not in STRIP_NAMES and not k.startswith(STRIP_PREFIX)}


def build(ks):
    binary = ROOT / "bin"
    binary.mkdir(exist_ok=True)
    cxx = os.environ.get("CXX", "g++")
    common = [cxx, "-std=c++20", "-O2", "-march=native", "-DLOCAL_BENCH"]
    checker = binary / "replay-checker"
    subprocess.run([cxx, "-std=c++20", "-O2",
                    str(ROOT / "src/replay-checker.cpp"), "-o", str(checker)],
                   check=True)
    for k in ks:
        exe = binary / ("esw-k%d" % k)
        cmd = common + ["-DPAPER_COUNT=%d" % k,
                        str(ROOT / "src/esw-paper-count.cpp"), "-o", str(exe)]
        print("Compiling K=%d" % k, flush=True)
        subprocess.run(cmd, check=True, env=environment())


def run_one(k, seed, input_dir, timeout, store_outputs):
    path = input_dir / ("%04d.txt" % seed)
    original = path.read_bytes()
    header, sep, rest = original.partition(b"\n")
    if not sep or tuple(map(int, header.split())) != (64, 192, 256, 1024):
        raise ValueError("%s: expected original 64 192 256 1024" % path)
    changed = ("64 %d 256 1024\n" % k).encode("ascii") + rest
    exe = ROOT / "bin" / ("esw-k%d" % k)
    start = time.perf_counter()
    cp = subprocess.run([str(exe)], input=changed, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, env=environment(), timeout=timeout)
    wall = time.perf_counter() - start
    if cp.returncode:
        raise RuntimeError("K=%d seed=%d solver exit=%d, stderr=%s"
                           % (k, seed, cp.returncode,
                              cp.stderr.decode("utf8", errors="replace")[-1000:]))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "output.txt"
        out.write_bytes(cp.stdout)
        checked = subprocess.run(
            [str(ROOT / "bin/replay-checker"), str(path), str(out), str(k)],
            capture_output=True, text=True, timeout=30)
        verdict = json.loads(checked.stdout)
    if checked.returncode or not verdict.get("valid") or verdict.get("errors") != 0:
        raise RuntimeError("K=%d seed=%d checker=%s" % (k, seed, verdict))
    if store_outputs:
        import gzip
        saved = ROOT / "runs" / ("k%d" % k)
        saved.mkdir(parents=True, exist_ok=True)
        with gzip.open(saved / ("%04d.out.gz" % seed), "wb") as f:
            f.write(cp.stdout)
        (saved / ("%04d.err" % seed)).write_bytes(cp.stderr)
    return {
        "K": k, "seed": seed, "total_moves": verdict["moves"],
        "mean_moves": verdict["moves"] / verdict["requests"],
        "score": verdict["score"], "errors": verdict["errors"],
        "max_request_moves": verdict["max_request_moves"],
        "wall_sec": round(wall, 6),
        "output_sha256": hashlib.sha256(cp.stdout).hexdigest(),
    }


def save_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, default=REPO_ROOT / "tools/in")
    p.add_argument("--ks", nargs="+", type=int, default=list(KS))
    p.add_argument("--cases", type=int, default=100)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--store-outputs", action="store_true")
    args = p.parse_args()
    if args.cases < 1 or args.cases > 100:
        p.error("This paired study uses at most the first 100 seeds")
    if not set(args.ks) <= set(range(182, 203)):
        p.error("Supported K range: 182..202")
    if not (args.input_dir / "0000.txt").is_file():
        p.error("Input directory missing: %s" % args.input_dir)
    args.ks = sorted(set(args.ks))
    build(args.ks)
    jobs = [(k, s) for k in args.ks for s in range(args.cases)]
    collected = []
    with futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i, row in enumerate(pool.map(
                lambda job: run_one(*job, args.input_dir, args.timeout,
                                    args.store_outputs), jobs), 1):
            collected.append(row)
            if i % 25 == 0 or i == len(jobs):
                print("%d/%d completed" % (i, len(jobs)), flush=True)
    dest = ROOT / "results"
    collected.sort(key=lambda row: (row["K"], row["seed"]))
    save_csv(dest / "reproduced_per_case.csv", collected,
             list(collected[0].keys()))
    baseline = {row["seed"]: row["mean_moves"] for row in collected if row["K"] == 192}
    summary = []
    for k in args.ks:
        group = [row for row in collected if row["K"] == k]
        values = [r["mean_moves"] for r in group]
        if len(values) != args.cases:
            raise RuntimeError("Missing runs for K=%d" % k)
        delta = [r["mean_moves"] - baseline[r["seed"]] for r in group] if len(baseline) == args.cases else []
        # t_0.975,99 (valid when --cases=100); otherwise leave CI blank.
        half_width = 1.984217 * statistics.stdev(delta) / len(delta)**0.5 if len(delta) == 100 else None
        summary.append({
            "K": k, "cases": len(values), "mean_moves": statistics.mean(values),
            "delta_vs_192": statistics.mean(delta) if delta else "",
            "delta_ci95_low": statistics.mean(delta) - half_width if half_width is not None else "",
            "delta_ci95_high": statistics.mean(delta) + half_width if half_width is not None else "",
            "errors": sum(r["errors"] for r in group),
        })
    save_csv(dest / "reproduced_summary.csv", summary, list(summary[0]))
    print("Wrote", dest / "reproduced_per_case.csv")
    print("Wrote", dest / "reproduced_summary.csv")
    print("Study reports are in REPORT_ja.md; this runner does not regenerate the original CPU-timing breakdown.")


if __name__ == "__main__":
    main()
