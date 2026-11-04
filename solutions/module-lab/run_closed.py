"""Paired search of unrestricted and optimized triangular opacity in the toy model."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory = Path(__file__).resolve().parent / "closed-results"
directory.mkdir(exist_ok=True)
jobs = [(k, q, seed, triangle) for k in (7, 8) for q in (0.1, 0.3, 0.5)
        for seed in (1, 2, 3) for triangle in (1, 0)]

def job(item):
    k, q, seed, triangle = item
    name = f"k{k}-q{int(q*100):02d}-s{seed}-t{triangle}"
    path = directory / f"{name}.json"
    if path.exists(): return json.loads(path.read_text())
    command = ["/tmp/ahc074-module-v2", f"K={k}", f"q={q}", f"seed={seed}",
               f"triangle={triangle}", "iters=1000", "seconds=300"]
    with (directory / f"{name}.err").open("w") as log:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=log, text=True, check=True, timeout=500)
    record = json.loads(result.stdout)
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(name, record["baseline"], record["best"], record["best"]-record["baseline"], flush=True)
    return record

with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(job, jobs))
(directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
