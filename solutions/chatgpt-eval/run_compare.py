#!/usr/bin/env python3
"""Run unmodified pahcer_run comparison logic with an explicitly identified C++ tester port."""
import argparse
import base64
import datetime
import gzip
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import pahcer_run as runner


def ensure_adapter(root: Path) -> Path:
    source = Path(__file__).with_name("tester.cpp")
    binary = root / "runs" / ".chatgpt-tester"
    binary.parent.mkdir(exist_ok=True)
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        temporary = binary.with_name(binary.name + f".{os.getpid()}.tmp")
        subprocess.run(["g++", "-std=c++23", "-O2", str(source), "-o", str(temporary)], check=True)
        temporary.replace(binary)
    return binary


def fsync_path(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def atomic_bytes(path: Path, data: bytes) -> None:
    """Materialize parent-owned immutable bytes without child regular-file descriptors."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError(f"short write: {written}/{len(data)}")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_bytes(case: dict, stdout: bytes, stderr: bytes, input_bytes: bytes) -> str | None:
    """Judge and independently replay authoritative PIPE captures, before any file reads."""
    case["stdout_bytes"] = len(stdout)
    case["stderr_bytes"] = len(stderr)
    case["stdout_sha256"] = hashlib.sha256(stdout).hexdigest()
    case["stderr_sha256"] = hashlib.sha256(stderr).hexdigest()
    case["input_sha256"] = hashlib.sha256(input_bytes).hexdigest()
    try:
        scores = runner.SCORE_LINE.findall(stderr.decode(errors="replace"))
        if case["score"] > 0:
            if not scores or int(scores[-1]) != case["score"]:
                return "captured stderr does not match the parsed score"
            inp = runner.replay.parse_input(input_bytes.decode())
            parsed = runner.replay.parse_output(inp, stdout.decode())
            if len(parsed.designs) == inp.k:
                canonical_design = ("\n".join(paper.pattern for paper in parsed.designs) + "\n").encode()
                case["paper_design_sha256"] = hashlib.sha256(canonical_design).hexdigest()
            checked = runner.replay.replay(inp, parsed, check=True)
            if checked.error or checked.score != case["score"]:
                return f"captured stdout replay failed: error={checked.error!r}, replay={checked.score}, judge={case['score']}"
            case["visibility_replay_verified"] = True
    except (ValueError, UnicodeError, IndexError) as error:
        return f"capture verification failed: {type(error).__name__}: {error}"
    return None


def verify_case(case: dict, run_dir: Path, in_dir: Path) -> str | None:
    """Verify the saved transcript independently, retaining raw judge scores on failure."""
    seed = case["seed"]
    out_path = run_dir / "out" / f"{seed:04d}.txt"
    err_path = run_dir / "err" / f"{seed:04d}.txt"
    try:
        fsync_path(out_path)
        fsync_path(err_path)
        stdout = out_path.read_bytes()
        stderr = err_path.read_bytes()
        return verify_bytes(case, stdout, stderr, (in_dir / f"{seed:04d}.txt").read_bytes())
    except (OSError, ValueError, UnicodeError, IndexError) as error:
        return f"saved transcript verification failed: {type(error).__name__}: {error}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--compare", nargs="+")
    modes.add_argument("--extend", nargs="+")
    parser.add_argument("--seeds")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("-c", "--comment", default="")
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    if args.extend and args.no_record:
        parser.error("--extend preserves the original run's record setting")
    args.solution = None
    args.comment = "[C++ tester port; original paired runner] " + args.comment
    template = tomllib.loads((ROOT / "pahcer_config.toml").read_text())
    template["test"]["threads"] = args.threads
    # Fresh generated cases deliberately use ids outside official seeds 0..1999.
    # Expand only this process's accepted range, after requiring every input file.
    if args.seeds and (m := re.fullmatch(r"(\d+)-(\d+)", args.seeds)):
        lo, hi = map(int, m.groups())
        for case_id in range(lo, hi):
            path = ROOT / "tools" / "in" / f"{case_id:04d}.txt"
            if not path.is_file():
                parser.error(f"input is missing: {path}")
        template["test"]["start_seed"] = min(lo, template["test"]["start_seed"])
        template["test"]["end_seed"] = max(hi, template["test"]["end_seed"])
    # No shared source/config file is changed. The paired aggregation is reused;
    # subprocess capture and metrics use authoritative parent-owned bytes.
    runner.ensure_tester = ensure_adapter
    infrastructure_failures = []
    materialization_recoveries = []
    # Retain every authoritative capture until after the archive is persisted and
    # all metrics are computed. No score or metric depends on saved child output.
    captures = {}
    archive_path = ROOT / "runs" / ("transcript-capture-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:10] + ".json.gz")
    archive_info = None

    def materialize(entry, recover=False):
        run_dir = Path(entry["run_dir"])
        seed = entry["record"]["seed"]
        for channel, folder in (("stdout", "out"), ("stderr", "err")):
            path = run_dir / folder / f"{seed:04d}.txt"
            data = entry[channel]
            if recover and path.exists() and path.read_bytes() == data:
                continue
            atomic_bytes(path, data)
            if path.read_bytes() != data:
                raise OSError(f"parent atomic write/readback mismatch: {path}")
            if recover:
                materialization_recoveries.append({"run_id":run_dir.name,"seed":seed,"channel":channel})
                runner.log(f"TRANSCRIPT RECOVERY {run_dir.name} seed={seed} {channel}: restored retained PIPE capture; solver was not rerun")

    def compare_case(seed, order, binaries, run_dirs, in_dir, tester):
        input_bytes = (in_dir / f"{seed:04d}.txt").read_bytes()
        records = [{} for _ in binaries]
        for i in order:
            run_dir = run_dirs[i]
            error = ""
            started = time.perf_counter()
            try:
                process = subprocess.run([str(tester), str(binaries[i])], input=input_bytes,
                                         capture_output=True, timeout=runner.COMPARE_CASE_TIMEOUT)
                stdout, stderr, returncode = process.stdout, process.stderr, process.returncode
            except subprocess.TimeoutExpired as expired:
                stdout, stderr, returncode = expired.stdout or b"", expired.stderr or b"", None
                error = f"timeout ({runner.COMPARE_CASE_TIMEOUT:.0f} s)"
            elapsed = time.perf_counter() - started
            text = stderr.decode(errors="replace")
            scores = runner.SCORE_LINE.findall(text)
            score = int(scores[-1]) if scores and not error else 0
            if not error and score == 0:
                error = runner.judge_message(text)
            case = {"seed":seed,"score":score,"relative_score":0.0,"execution_time":elapsed,
                    "error_message":error,"tester_returncode":returncode,"transcript_source":"parent PIPE capture"}
            failure = verify_bytes(case, stdout, stderr, input_bytes)
            if returncode not in (0, None) and score > 0:
                failure = f"tester returned {returncode} despite a positive score"
            if failure:
                case["raw_judge_score"] = case["score"]
                case["score"] = 0
                case["error_message"] = "infrastructure verification failed: " + failure
                case["infrastructure_error"] = failure
                infrastructure_failures.append((str(run_dir), seed, failure))
                runner.log(f"INFRASTRUCTURE ERROR {run_dir.name} seed={seed}: {failure}")
            entry = {"run_dir":str(run_dir),"input":input_bytes,"stdout":stdout,"stderr":stderr,"record":case}
            captures[(str(run_dir),seed)] = entry
            try:
                materialize(entry)
            except OSError as failure:
                # Keep authoritative bytes and retry materialization explicitly at
                # batch end; this never reruns a solver or changes its score.
                runner.log(f"TRANSCRIPT STORAGE WARNING {run_dir.name} seed={seed}: {failure}")
            records[i] = case
        return records
    runner.compare_case = compare_case

    def ensure_archive():
        nonlocal archive_info
        if archive_info is not None:
            return archive_info
        inputs = {}
        entries = []
        for (run,seed),entry in sorted(captures.items()):
            inputs[str(seed)] = {"sha256":hashlib.sha256(entry["input"]).hexdigest(),
                                 "base64":base64.b64encode(entry["input"]).decode("ascii")}
            entries.append({"run_id":Path(run).name,"record":entry["record"],
                            "stdout_base64":base64.b64encode(entry["stdout"]).decode("ascii"),
                            "stderr_base64":base64.b64encode(entry["stderr"]).decode("ascii")})
        evidence = {"format":"ahc074-pipe-capture-v1","description":"Authoritative immutable PIPE captures; scores and visibility replay were computed before file materialization.",
                    "environment":{k:os.environ[k] for k in ("MAP_ITERS","GOPT_STEPS","ANNEAL_ITERS","CLIMB_ITERS") if k in os.environ},
                    "inputs":inputs,"entries":entries}
        plain = json.dumps(evidence,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
        compressed = gzip.compress(plain,mtime=0)
        atomic_bytes(archive_path, compressed)
        if archive_path.read_bytes() != compressed:
            raise RuntimeError("authoritative capture archive failed atomic write/readback verification")
        archive_info = {"path":str(archive_path.relative_to(ROOT)),"sha256":hashlib.sha256(compressed).hexdigest(),
                        "uncompressed_sha256":hashlib.sha256(plain).hexdigest(),"cases":len(entries),"format":evidence["format"]}
        runner.log(f"Authoritative PIPE archive saved and verified: {archive_info['path']}")
        return archive_info

    def compute_metrics(run_dir):
        ensure_archive()
        entries = [entry for (run,seed),entry in captures.items() if run == str(run_dir)]
        if not entries:
            raise RuntimeError("no authoritative captures available for metrics")
        metrics = {}
        for entry in sorted(entries,key=lambda e:e["record"]["seed"]):
            record = entry["record"]
            inp = runner.replay.parse_input(entry["input"].decode())
            out = runner.replay.parse_output(inp,entry["stdout"].decode(errors="replace"))
            metric = runner.replay.case_metrics(inp,out)
            metric["stderr"] = runner.replay.stderr_stats(entry["stderr"].decode(errors="replace"))
            metric["judge_score"] = record["score"]
            metric["execution_time"] = record["execution_time"]
            metrics[record["seed"]] = metric
        atomic_bytes(run_dir / "metrics.json",json.dumps({"version":runner.replay.METRICS_VERSION,
                     "source":"authoritative PIPE captures","cases":{str(k):v for k,v in metrics.items()}}).encode())
        return metrics
    runner.compute_metrics = compute_metrics
    signal.signal(signal.SIGTERM, runner._raise_interrupted)
    print("[chatgpt-eval] tester.cpp is a C++ port, not the official Rust binary", flush=True)
    print(f"[chatgpt-eval] threads={args.threads}; compiler flags={runner.COMPILE_CMD}", flush=True)
    # Other agents may prepare runs concurrently before acquiring runs/.lock.
    # Track only this invocation's arms, rather than scanning all new directories.
    tracked = []
    original_prepare = runner.prepare_run
    def prepare(*values, **keywords):
        arm = original_prepare(*values, **keywords)
        tracked.append(arm["run_dir"] / "meta.json")
        return arm
    runner.prepare_run = prepare
    if args.extend:
        for value in args.extend:
            run_dir = runner.replay.resolve_run(value)
            path = run_dir / "meta.json"
            tracked.append(path)
            prior = json.loads(path.read_text()).get("capture_archive")
            if not prior:
                parser.error("--extend requires a run with a verified PIPE capture archive; legacy runs must be compared afresh")
            raw = (ROOT / prior["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != prior["sha256"]:
                parser.error(f"prior capture archive hash mismatch: {prior['path']}")
            evidence = json.loads(gzip.decompress(raw))
            for item in evidence["entries"]:
                if item["run_id"] != run_dir.name:
                    continue
                record = item["record"]
                captures[(str(run_dir),record["seed"])] = {"run_dir":str(run_dir),"record":record,
                    "input":base64.b64decode(evidence["inputs"][str(record["seed"])]["base64"]),
                    "stdout":base64.b64decode(item["stdout_base64"]),"stderr":base64.b64decode(item["stderr_base64"])}
    result = runner.evaluate_extend(args, ROOT, template) if args.extend else runner.evaluate_compare(args, ROOT, template)
    # Persist provenance together with every new run, without changing evaluation results.
    source = Path(__file__).with_name("tester.cpp")
    provenance = {"implementation": "C++ port of tools/src/lib.rs, not official Rust binary",
                  "ported_reference_commit": "dee23c8fce0eba04e513478629402f20b843e9f0",
                  "source": str(source.relative_to(ROOT)),
                  "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "threads": args.threads,
                  "durability": "PIPE capture; in-memory score and visibility replay; parent atomic materialization; retained captures; verified gzip archive"}
    if captures:
        ensure_archive()
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != archive_info["sha256"]:
            raise RuntimeError("authoritative capture archive changed after verification")
        for entry in captures.values():
            try:
                materialize(entry,recover=True)
            except OSError as failure:
                infrastructure_failures.append((entry["run_dir"],entry["record"]["seed"],str(failure)))
    for path in tracked:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        data["tester_adapter"] = provenance
        data["evaluation_environment"] = {k:os.environ[k] for k in ("MAP_ITERS","GOPT_STEPS","ANNEAL_ITERS","CLIMB_ITERS") if k in os.environ}
        data["capture_archive"] = archive_info
        data["transcript_recoveries"] = [r for r in materialization_recoveries if r["run_id"] == path.parent.name]
        result_path = path.parent / "result.json"
        if result_path.exists():
            for case in json.loads(result_path.read_text())["cases"]:
                for channel in ("stdout", "stderr"):
                    expected = case.get(channel + "_sha256")
                    if expected is None:
                        continue
                    transcript = path.parent / ("out" if channel == "stdout" else "err") / f"{case['seed']:04d}.txt"
                    actual = hashlib.sha256(transcript.read_bytes()).hexdigest()
                    if actual != expected:
                        failure = f"{channel} changed after per-case verification"
                        infrastructure_failures.append((str(path.parent), case["seed"], failure))
        own_failures = [{"seed":seed,"error":error} for run,seed,error in infrastructure_failures if run == str(path.parent)]
        data["transcript_integrity"] = {"verified": not own_failures, "failures": own_failures}
        if own_failures:
            data["status"] = "invalid_infrastructure"
        runner.save_meta(path.parent, data)
        fsync_path(path)
        if result_path.exists(): fsync_path(result_path)
    if infrastructure_failures:
        runner.log(f"INFRASTRUCTURE FAILURE: {len(infrastructure_failures)} transcript errors; this comparison is invalid. No automatic retries were made.")
        return 2
    return result


if __name__ == "__main__":
    raise SystemExit(main())
