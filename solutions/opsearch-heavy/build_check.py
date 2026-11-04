"""Compile both deliverables sequentially under the evaluation lock; execute no binaries."""
import fcntl
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
results = []
print("Waiting for the evaluation lock before sequential builds.", flush=True)
with Path("/home/sato/ahc074/runs/.lock").open("rb") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for solution in ("opsearch-heavy", "opsearch-fast"):
        for compiler, defines in (("clang++", ["-DLOCAL_BENCH"]), ("g++", [])):
            target = root / "solutions" / solution
            output = target / ".build-check"
            command = [compiler, "-std=c++23", "-O2", *defines, str(target / "main.cpp"), "-o", str(output)]
            print(" ".join(command), flush=True)
            result = subprocess.run(command, capture_output=True, text=True)
            results.append({"solution": solution, "command": command, "exit_code": result.returncode,
                            "stdout": result.stdout, "stderr": result.stderr})
            if output.exists():
                output.unlink()
            if result.returncode:
                print(result.stderr, flush=True)
                break
        if results[-1]["exit_code"]:
            break
(Path(__file__).resolve().parent / "build-check.json").write_text(json.dumps(results, indent=2) + "\n")
assert len(results) == 4 and all(r["exit_code"] == 0 for r in results)
print("Clang LOCAL_BENCH and GCC submission builds passed for both solutions.", flush=True)
