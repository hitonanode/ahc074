#!/usr/bin/env python3
"""Use the repository paired runner, committing complete per-case logs atomically."""
import argparse
import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import pahcer_run


def atomic_write(path: Path, data: bytes) -> None:
    """Publish a complete file once; never expose a growing final log file.

    The same-directory rename keeps publication atomic. The final filename is
    untouched while the solver is running, avoiding snapshots of partial logs.
    """
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Refusing to write outside the repository: {path}")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError(f"Short write for {path}: {written}/{len(data)}")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_compare_case(seed: int, order: list[int], binaries: list[Path], run_dirs: list[Path],
                        in_dir: Path, tester: Path) -> list[dict]:
    """Same per-case ordering, timeout and verdict rules as pahcer_run.compare_case.

    Only log transport changes: both streams stay in memory until process exit,
    then each complete stream is committed by atomic rename. Score extraction
    reads that same captured stderr, and hashes preserve its provenance in the
    result record. The source snapshot, lock and aggregate statistics remain
    those of the repository runner.
    """
    seed4 = f"{seed:04d}"
    infile = in_dir / f"{seed4}.txt"
    records: list[dict] = [{} for _ in binaries]
    for i in order:
        outfile = run_dirs[i] / "out" / f"{seed4}.txt"
        errfile = run_dirs[i] / "err" / f"{seed4}.txt"
        error = ""
        start = time.perf_counter()
        with open(infile, "rb") as stdin:
            try:
                done = subprocess.run([str(tester), str(binaries[i])], stdin=stdin,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      timeout=pahcer_run.COMPARE_CASE_TIMEOUT)
                stdout_bytes, stderr_bytes = done.stdout, done.stderr
            except subprocess.TimeoutExpired as expired:
                error = f"timeout ({pahcer_run.COMPARE_CASE_TIMEOUT:.0f} s)"
                stdout_bytes = expired.stdout or b""
                stderr_bytes = expired.stderr or b""
        atomic_write(outfile, stdout_bytes)
        atomic_write(errfile, stderr_bytes)
        elapsed = time.perf_counter() - start
        err_text = stderr_bytes.decode(errors="replace")
        scores = pahcer_run.SCORE_LINE.findall(err_text)
        score = int(scores[-1]) if scores and not error else 0
        if not error and score == 0:
            error = pahcer_run.judge_message(err_text)
        records[i] = {
            "seed": seed, "score": score, "relative_score": 0.0,
            "execution_time": elapsed, "error_message": error,
            "log_storage": "atomic-from-pipes",
            "stdout_bytes": len(stdout_bytes), "stderr_bytes": len(stderr_bytes),
            "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
        }
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", nargs="+", required=True)
    parser.add_argument("--seeds", default="5000-5128")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("-c", "--comment", default="")
    args = parser.parse_args()
    template = tomllib.loads((ROOT / "pahcer_config.toml").read_text())
    start, end = map(int, args.seeds.split("-"))
    template["test"].update(start_seed=start, end_seed=end, threads=args.threads)
    signal.signal(signal.SIGTERM, pahcer_run._raise_interrupted)
    pahcer_run.compare_case = atomic_compare_case
    return pahcer_run.evaluate_compare(args, ROOT, template)


if __name__ == "__main__":
    sys.exit(main())
