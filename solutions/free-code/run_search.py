"""Free-printing structure search; it never reads the saved request sequence."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory = Path(__file__).resolve().parent / "results"
directory.mkdir(exist_ok=True)
jobs = [(case, start, temp) for case in (24, 25, 26, 27)
        for start, temp in (("base", .04), ("base", .12), ("balanced", .12), ("random", .12))]

def job(item):
    case, start, temp = item
    name = f"{case:04d}-{start}-t{int(temp*100):02d}"
    path = directory / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    command = ["/tmp/ahc074-free-code", f"/home/sato/ahc074/tools/in/{case:04d}.txt",
               f"/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{case:04d}.txt",
               f"start={start}", f"temp={temp}", "iters=50000", "seconds=300"]
    with (directory / f"{name}.err").open("w") as log:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=log, text=True, check=True, timeout=500)
    row = json.loads(result.stdout)
    row.update(case=case, start=start, temp=temp)
    path.write_text(json.dumps(row, indent=2) + "\n")
    print(name, row["baseline_exact"], row["best_exact"], row["matched"], row["nonlinear"], flush=True)
    return row

with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(job, jobs))
(directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
