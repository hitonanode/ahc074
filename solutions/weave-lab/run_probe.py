"""Aggregate structural counts from saved runs; no solver is executed."""
import concurrent.futures
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay

run = replay.resolve_run(sys.argv[1] if len(sys.argv) > 1 else "20261103-033246_as6-canon")
lo, hi = map(int, sys.argv[2].split("-")) if len(sys.argv) > 2 else (24, 88)
binary = "/tmp/ahc074-weave-probe"

def job(seed):
    result = subprocess.run([binary, str(replay.main_root() / "tools" / "in" / f"{seed:04d}.txt"),
                             str(replay.out_path(run, seed))], check=True, text=True, capture_output=True)
    return {"seed": seed, **json.loads(result.stdout)}

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows = list(pool.map(job, range(lo, hi)))
keys = [k for k, v in rows[0].items() if isinstance(v, (int, float)) and k != "seed"]
summary = {k: {"mean": statistics.mean(r[k] for r in rows),
               "se": statistics.stdev(r[k] for r in rows) / len(rows)**0.5 if len(rows) > 1 else 0}
           for k in keys}
out = Path(__file__).resolve().parent / f"probe-{lo}-{hi}.json"
out.write_text(json.dumps({"run": run.name, "seeds": [lo, hi], "summary": summary, "rows": rows}, indent=2) + "\n")
print(json.dumps({"run": run.name, "n": len(rows), "summary": summary}, indent=2))
