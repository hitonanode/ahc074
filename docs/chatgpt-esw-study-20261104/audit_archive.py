#!/usr/bin/env python3
"""Replay retained AHC074 outputs; this does not rerun or benchmark the solvers."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
import zipfile

ARCHIVE_SHA256 = "8ec68edeb35809ebe98fb78a30fe6a80d38fd162e571dc827603e7befc825f1c"
CHECKER_SHA256 = "9471fb7184dbd9ecc9b285d704e60cd505ccf055639394702c80a91d3669385c"
ROOT = "ahc074_no_fallback_research/"
METHODS = ("base-full", "mdp-only", "batch-extract", "local-two", "local-four")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(archive: Path, cxx: str) -> dict:
    require(digest(archive.read_bytes()) == ARCHIVE_SHA256, "Archive SHA-256 mismatch")
    csv_path = Path(__file__).resolve().parent / "results" / "paired64.csv"
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    paired = {int(row["case"]): row for row in rows}
    require(len(rows) == 64 and set(paired) == set(range(100, 164)), "Unexpected CSV cases")
    totals = dict.fromkeys(METHODS, 0)
    records = []
    design_hashes = {}
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory(prefix="ahc074-audit-") as tmp:
        work = Path(tmp)
        source = z.read(ROOT + "src/judge.cpp")
        require(digest(source) == CHECKER_SHA256, "Checker SHA-256 mismatch")
        source_path, binary = work / "judge.cpp", work / "judge"
        source_path.write_bytes(source)
        subprocess.run([cxx, "-std=c++20", "-O2", str(source_path), "-o", str(binary)],
                       check=True, capture_output=True, text=True, timeout=120)
        manifest = json.loads(z.read(ROOT + "results/audit_final64.json"))
        old = {(int(r["case"]), r["method"]): r for r in manifest["records"]}
        expected = {(case, method) for case in paired for method in METHODS}
        require(len(manifest["records"]) == 320 and set(old) == expected,
                "Unexpected or duplicate output records")
        for case in sorted(paired):
            input_path = work / "input.txt"
            input_data = z.read(ROOT + f"inputs/validation/{case:04}.txt")
            input_path.write_bytes(input_data)
            reference_design = None
            for method in METHODS:
                previous = old[case, method]
                member = previous["output"]
                require(member.startswith("results/") and ".." not in member.split("/"),
                        "Unsafe archive member")
                data = z.read(ROOT + member)
                require(digest(data) == previous["sha256"], f"Output hash: {case}/{method}")
                output_path = work / "output.txt"
                output_path.write_bytes(data)
                run = subprocess.run([str(binary), str(input_path), str(output_path)],
                                     capture_output=True, text=True, timeout=30)
                require(run.returncode == 0, f"Replay failed {case}/{method}: {run.stdout} {run.stderr}")
                result = json.loads(run.stdout)
                expected_moves = int(paired[case][method])
                require(result.get("valid") is True and result["errors"] == 0,
                        f"Invalid or wrong display: {case}/{method}")
                require(result["moves"] == expected_moves == previous["moves"],
                        f"Move mismatch: {case}/{method}")
                require(result["score"] == expected_moves, f"Score mismatch: {case}/{method}")
                design = b"\n".join(data.splitlines()[:192]) + b"\n"
                if reference_design is None:
                    reference_design = design
                require(design == reference_design, f"Design mismatch: case {case}")
                log = z.read(ROOT + member[:-4] + ".err").decode("utf-8")
                fast = re.search(r"^fast_requests\s*=\s*(\d+)", log, re.MULTILINE)
                require(fast is not None and int(fast.group(1)) == 0,
                        f"Missing/nonzero fast_requests: {case}/{method}")
                totals[method] += expected_moves
                design_hashes[case] = digest(design)
                records.append({"case": case, "method": method, "moves": expected_moves,
                                "input_sha256": digest(input_data), "output_sha256": digest(data),
                                "design_sha256": digest(design)})
    stats = []
    for method in METHODS:
        base = [int(row["base-full"]) for row in rows]
        candidate = [int(row[method]) for row in rows]
        savings = [a - b for a, b in zip(base, candidate)]
        logs = [100.0 * math.log(b / a) for a, b in zip(base, candidate)]
        stats.append({"method": method, "cases": len(rows), "moves": sum(candidate),
                      "reduction_percent": 100.0 * (sum(base) - sum(candidate)) / sum(base),
                      "wins": sum(v > 0 for v in savings), "ties": sum(v == 0 for v in savings),
                      "losses": sum(v < 0 for v in savings),
                      "mean_saving_per_case": statistics.mean(savings),
                      "saving_se": statistics.stdev(savings) / math.sqrt(len(rows)),
                      "mean_log_ratio_percent": statistics.mean(logs),
                      "log_ratio_se_percent": statistics.stdev(logs) / math.sqrt(len(rows))})
    return {"audit_kind": "retained-output replay; no solver rerun or timing measurement",
            "archive_sha256": ARCHIVE_SHA256, "checker_sha256": CHECKER_SHA256,
            "checked_outputs": len(records), "cases": len(design_hashes),
            "errors": 0, "illegal_outputs": 0, "fast_requests": 0,
            "identical_designs_within_each_case": True, "moves": totals,
            "statistics": stats, "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.archive, args.cxx)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Validated {report['checked_outputs']} outputs; report: {args.output}")
        else:
            print(text, end="")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")


if __name__ == "__main__":
    main()
