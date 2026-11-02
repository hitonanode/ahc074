#!/usr/bin/env python3
"""Collect verified PIPE runs into auditable per-case CSV and paired comparisons.

Usage:
  python3 solutions/chatgpt-study/collect_results.py RUN_ID... --out-dir PATH

The authoritative inputs and transcripts come from each run's verified capture
archive. Legacy runs and infrastructure-invalid runs are rejected. Pairwise
statistics are produced only for identical seed sets and identical input hashes.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "dee23c8fce0eba04e513478629402f20b843e9f0"
sys.path.insert(0, str(ROOT / "scripts"))
import replay


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            require(stream.write(data) == len(data), f"short write: {path}")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        require(path.read_bytes() == data, f"write/readback mismatch: {path}")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def local_reference(value: str) -> Path:
    """Archive paths are repository-relative; refuse accidental outside paths."""
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), f"reference escapes repository: {value}")
    return path


def load_archive(reference: dict, cache: dict) -> dict:
    require(reference.get("format") == "ahc074-pipe-capture-v1", "verified PIPE archive required")
    path = local_reference(reference["path"])
    expected_hash = reference["sha256"]
    key = (str(path), expected_hash)
    if key in cache:
        return cache[key]
    raw = path.read_bytes()
    require(sha256(raw) == expected_hash, f"archive hash mismatch: {path}")
    plain = gzip.decompress(raw)
    if reference.get("uncompressed_sha256"):
        require(sha256(plain) == reference["uncompressed_sha256"], f"uncompressed archive hash mismatch: {path}")
    evidence = json.loads(plain)
    require(evidence.get("format") == reference["format"], f"archive format mismatch: {path}")
    inputs = {}
    for seed, item in evidence["inputs"].items():
        data = base64.b64decode(item["base64"], validate=True)
        require(sha256(data) == item["sha256"], f"input hash mismatch: {path}, seed {seed}")
        inputs[int(seed)] = (data, item["sha256"])
    entries = {}
    for item in evidence["entries"]:
        record = item["record"]
        entry_key = (item["run_id"], int(record["seed"]))
        require(entry_key not in entries, f"duplicate archive entry: {entry_key}")
        entries[entry_key] = item
    if reference.get("cases") is not None:
        require(len(entries) == reference["cases"], f"archive case count mismatch: {path}")
    loaded = {"inputs": inputs, "entries": entries, "environment": evidence.get("environment", {}),
              "path": str(path.relative_to(ROOT)), "sha256": expected_hash, "bytes": len(raw)}
    cache[key] = loaded
    return loaded


def resolve_exact_run(value: str) -> Path:
    candidate = Path(value)
    run = candidate.resolve() if candidate.is_dir() else (ROOT / "runs" / value).resolve()
    require(run.parent == (ROOT / "runs").resolve(), f"an exact runs/<run-id> is required: {value}")
    require(run.is_dir(), f"missing run: {run}")
    return run


def collect_run(run: Path, archive_cache: dict) -> tuple[dict, list[dict]]:
    meta_bytes = (run / "meta.json").read_bytes()
    result_bytes = (run / "result.json").read_bytes()
    meta, result = json.loads(meta_bytes), json.loads(result_bytes)
    require(meta.get("run_id") == run.name, f"run-id mismatch: {run}")
    require(meta.get("status") == "ok", f"run is not valid/finished: {run.name}: {meta.get('status')}")
    integrity = meta.get("transcript_integrity", {})
    require(integrity.get("verified") is True and not integrity.get("failures"), f"transcript integrity failed: {run.name}")
    require(meta.get("capture_archive"), f"legacy run has no authoritative PIPE archive: {run.name}")
    archive = load_archive(meta["capture_archive"], archive_cache)

    source = run / "src" / "main.cpp"
    source_bytes = source.read_bytes()
    require(bool(source_bytes), f"empty source snapshot: {source}")
    source_hash = sha256(source_bytes)
    compile_paths = {str(Path(token).resolve()) for token in meta.get("compile_command", []) if isinstance(token, str) and token.endswith((".cpp", ".cc", ".cxx"))}
    require(str(source.resolve()) in compile_paths, f"compile command does not reference snapshot main.cpp: {run.name}")
    # Older runner metadata did not record a source hash before compilation.
    # Do not pretend this newly computed hash is such a prior attestation.
    prior_source_hash = meta.get("source_snapshot_sha256")
    if prior_source_hash:
        require(prior_source_hash == source_hash, f"recorded source snapshot hash mismatch: {run.name}")
    source_manifest = {str(p.relative_to(run / "src")): sha256(p.read_bytes())
                       for p in sorted((run / "src").rglob("*")) if p.is_file()}
    source_manifest_hash = sha256(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")).encode())

    cases = {}
    for case in result["cases"]:
        seed = int(case["seed"])
        require(seed not in cases, f"duplicate result seed: {run.name}, {seed}")
        cases[seed] = case
    archive_seeds = {seed for name, seed in archive["entries"] if name == run.name}
    require(set(cases) == archive_seeds, f"result/archive seed sets differ: {run.name}")
    require(result.get("case_count") == len(cases), f"case count mismatch: {run.name}")
    environment = meta.get("evaluation_environment", {})
    allowed_environment = {"MAP_ITERS", "GOPT_STEPS", "ANNEAL_ITERS", "CLIMB_ITERS"}
    require(set(environment) <= allowed_environment, f"unexpected environment metadata: {run.name}")
    require(environment == archive["environment"], f"metadata/archive environment differs: {run.name}")

    rows = []
    for seed, case in sorted(cases.items()):
        item = archive["entries"][(run.name, seed)]
        record = item["record"]
        require(record.get("transcript_source") == "parent PIPE capture", f"non-PIPE case: {run.name}, {seed}")
        require(not record.get("infrastructure_error") and not case.get("infrastructure_error"), f"infrastructure-invalid case: {run.name}, {seed}")
        for key in ("score", "execution_time", "stdout_sha256", "stderr_sha256", "input_sha256", "paper_design_sha256"):
            require(case.get(key) == record.get(key), f"result/archive {key} mismatch: {run.name}, {seed}")
        stdout = base64.b64decode(item["stdout_base64"], validate=True)
        stderr = base64.b64decode(item["stderr_base64"], validate=True)
        for channel, data, folder in (("stdout", stdout, "out"), ("stderr", stderr, "err")):
            require(sha256(data) == record[channel + "_sha256"], f"{channel} hash mismatch: {run.name}, {seed}")
            require(len(data) == record[channel + "_bytes"], f"{channel} size mismatch: {run.name}, {seed}")
            materialized = run / folder / f"{seed:04d}.txt"
            require(materialized.read_bytes() == data, f"materialized {channel} differs from archive: {run.name}, {seed}")
        input_bytes, input_hash = archive["inputs"][seed]
        require(input_hash == record["input_sha256"], f"input reference mismatch: {run.name}, {seed}")
        inp = replay.parse_input(input_bytes.decode())
        parsed = replay.parse_output(inp, stdout.decode())
        rep = replay.replay(inp, parsed, check=True)
        score = int(record["score"])
        if score > 0:
            require(rep.error is None and rep.score == score, f"visibility replay mismatch: {run.name}, {seed}: {rep.error}, score {rep.score}/{score}")
            require(record.get("visibility_replay_verified") is True, f"capture lacks replay verification: {run.name}, {seed}")
            require(len(parsed.designs) == inp.k, f"incomplete paper design: {run.name}, {seed}")
            design_hash = sha256(("\n".join(p.pattern for p in parsed.designs) + "\n").encode())
            require(design_hash == record.get("paper_design_sha256"), f"paper design hash mismatch: {run.name}, {seed}")
            mistakes, moves = rep.game.mistakes, rep.game.moves
            require(score == 2 * inp.k * mistakes + moves, f"score formula mismatch: {run.name}, {seed}")
        else:
            design_hash, mistakes, moves = record.get("paper_design_sha256"), None, None
        solution = Path(meta["source"]["path"]).name
        rows.append({"run_id": run.name, "solution": solution, "seed": seed, "input_sha256": input_hash,
                     "status": "OK" if score > 0 else "WA", "score": score, "E": mistakes, "T": moves,
                     "requests": inp.r, "moves_per_query": moves / inp.r if moves is not None else None,
                     "runtime_sec": float(record["execution_time"]), "paper_design_sha256": design_hash,
                     "source_sha256": source_hash, "source_snapshot": str(source.relative_to(ROOT)),
                     "capture_archive": archive["path"], "capture_archive_sha256": archive["sha256"],
                     "stdout_sha256": record["stdout_sha256"], "stderr_sha256": record["stderr_sha256"]})

    # Detect concurrent mutation during collection; all checks concern these snapshots.
    require(source.read_bytes() == source_bytes, f"source snapshot changed while collecting: {run.name}")
    require((run / "meta.json").read_bytes() == meta_bytes, f"metadata changed while collecting: {run.name}")
    require((run / "result.json").read_bytes() == result_bytes, f"results changed while collecting: {run.name}")
    valid = [row for row in rows if row["score"] > 0]
    description = {"run_id": run.name, "solution": rows[0]["solution"] if rows else None,
                   "cases": len(rows), "seeds": sorted(cases), "WA": len(rows) - len(valid),
                   "mean_score": statistics.mean(r["score"] for r in valid) if valid else None,
                   "mean_E": statistics.mean(r["E"] for r in valid) if valid else None,
                   "mean_T": statistics.mean(r["T"] for r in valid) if valid else None,
                   "mean_moves_per_query": statistics.mean(r["moves_per_query"] for r in valid) if valid else None,
                   "mean_runtime_sec": statistics.mean(r["runtime_sec"] for r in rows) if rows else None,
                   "max_runtime_sec": max((r["runtime_sec"] for r in rows), default=None),
                   "over_2_seconds": sum(r["runtime_sec"] > 2 for r in rows),
                   "source_base_commit": BASE_COMMIT, "source_sha256": source_hash,
                   "source_snapshot": str(source.relative_to(ROOT)), "source_manifest": source_manifest,
                   "source_manifest_sha256": source_manifest_hash,
                   "source_hash_validation": {"compile_command_references_snapshot": True,
                                              "stable_read_during_collection": True,
                                              "previously_recorded_expected_hash": prior_source_hash},
                   "compiler": meta.get("compiler"), "compile_command": meta.get("compile_command"),
                   "evaluation_environment": environment, "capture_archive": meta["capture_archive"],
                   "meta_integrity_verified": True, "archive_hash_verified": True,
                   "visibility_replay_verified_cases": len(valid), "materialized_transcripts_match": True,
                   "transcript_recoveries": meta.get("transcript_recoveries", []),
                   "comment": meta.get("comment"), "compare_group": meta.get("compare", {}).get("runs")}
    return description, rows


def pairwise(a: dict, b: dict, rows_a: list[dict], rows_b: list[dict]) -> dict:
    left = {row["seed"]: row for row in rows_a}
    right = {row["seed"]: row for row in rows_b}
    result = {"a": a["run_id"], "b": b["run_id"], "definition": "log(score_b / score_a); negative favors b; W/D/L are b versus a"}
    if set(left) != set(right):
        return {**result, "status": "not_compared", "reason": "seed sets differ", "cases_a": len(left), "cases_b": len(right),
                "only_a": sorted(set(left) - set(right)), "only_b": sorted(set(right) - set(left))}
    different_inputs = [seed for seed in left if left[seed]["input_sha256"] != right[seed]["input_sha256"]]
    if different_inputs:
        return {**result, "status": "not_compared", "reason": "input hashes differ for the same seed labels", "seeds": sorted(different_inputs)}
    seeds = [seed for seed in sorted(left) if left[seed]["score"] > 0 and right[seed]["score"] > 0]
    ratios = [math.log(right[s]["score"] / left[s]["score"]) for s in seeds]
    mean = statistics.mean(ratios) if ratios else None
    se = statistics.stdev(ratios) / math.sqrt(len(ratios)) if len(ratios) > 1 else None
    return {**result, "status": "compared", "matched_cases": len(left), "valid_pairs": len(seeds),
            "excluded_seeds_with_WA": sorted(set(left) - set(seeds)),
            "mean_log_ratio_b_over_a": mean, "standard_error": se,
            "mean_log_ratio_percent": 100 * mean if mean is not None else None,
            "standard_error_percent": 100 * se if se is not None else None,
            "geometric_score_change_percent": 100 * math.expm1(mean) if mean is not None else None,
            "wins_b": sum(right[s]["score"] < left[s]["score"] for s in seeds),
            "draws": sum(right[s]["score"] == left[s]["score"] for s in seeds),
            "losses_b": sum(right[s]["score"] > left[s]["score"] for s in seeds),
            "b_better_by_two_standard_errors": mean < -2 * se if mean is not None and se is not None else None,
            "identical_paper_design_cases": sum(left[s]["paper_design_sha256"] == right[s]["paper_design_sha256"] for s in seeds),
            "evaluation_environment_identical": a["evaluation_environment"] == b["evaluation_environment"],
            "same_paired_group": a["compare_group"] == b["compare_group"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path,
                        help="copy each unique verified compressed archive once for inclusion in the PR")
    args = parser.parse_args()
    runs = [resolve_exact_run(value) for value in args.run_ids]
    require(len(set(runs)) == len(runs), "duplicate run-id argument")
    archive_cache = {}
    descriptions, rows_by_run = [], []
    for run in runs:
        description, rows = collect_run(run, archive_cache)
        descriptions.append(description)
        rows_by_run.append(rows)
        print(f"verified {run.name}: {len(rows)} cases; mean score={description['mean_score']}; source={description['source_sha256']}")
    comparisons = [pairwise(descriptions[i], descriptions[j], rows_by_run[i], rows_by_run[j])
                   for i in range(len(runs)) for j in range(i + 1, len(runs))]
    all_rows = [row for rows in rows_by_run for row in rows]
    require(bool(all_rows), "no case records")
    delivered_archives = []
    if args.evidence_dir:
        for archive in archive_cache.values():
            original = local_reference(archive["path"])
            destination = (args.evidence_dir / original.name).resolve()
            require(destination.is_relative_to(ROOT), "evidence directory must be inside the repository")
            data = original.read_bytes()
            require(sha256(data) == archive["sha256"], f"archive changed before copying: {original}")
            if not destination.exists() or destination.read_bytes() != data:
                atomic_write(destination, data)
            delivered_archives.append({"original_archive": archive["path"],
                                       "path": str(destination.relative_to(ROOT)),
                                       "sha256": archive["sha256"], "bytes": len(data)})
        delivery_map = {item["original_archive"]: item for item in delivered_archives}
        for row in all_rows:
            row["evidence_archive"] = delivery_map[row["capture_archive"]]["path"]
        for description in descriptions:
            description["evidence_archive"] = delivery_map[description["capture_archive"]["path"]]
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=list(all_rows[0]))
    writer.writeheader()
    writer.writerows(all_rows)
    summary = {"format": "ahc074-verified-comparison-v1", "source_base_commit": BASE_COMMIT,
               "method": "Scores and E/T replayed from verified PIPE archive bytes; pairwise joins require identical seed sets and input hashes; WAs excluded from ratios.",
               "runs": descriptions, "pairwise": comparisons,
               "delivery_evidence": delivered_archives,
               "verified_archive_files": [{"path": v["path"], "sha256": v["sha256"], "bytes": v["bytes"]} for v in archive_cache.values()]}
    # No output is produced until every requested run has passed validation.
    atomic_write(args.out_dir / "per_case.csv", csv_buffer.getvalue().encode())
    atomic_write(args.out_dir / "summary.json", (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode())
    print(f"wrote {len(all_rows)} case rows and {len(comparisons)} pairwise records to {args.out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, AssertionError) as error:
        print(f"collection refused: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2)
