from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory = Path(__file__).resolve().parent / "models"
directory.mkdir(exist_ok=True)
jobs = [(case, price) for case in range(24, 32) for price in (2.6, 3.0)]

def job(item):
    case, price = item
    name = f"{case:04d}-p{int(price*10):02d}"
    path = directory / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    command = ["/tmp/ahc074-patch-probe", f"/home/sato/ahc074/tools/in/{case:04d}.txt",
               f"/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{case:04d}.txt",
               f"price={price}", "iters=1000000", "seconds=60"]
    with (directory / f"{name}.err").open("w") as log:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=log, text=True, check=True, timeout=150)
    row = json.loads(result.stdout)
    row.update(case=case)
    path.write_text(json.dumps(row, indent=2) + "\n")
    print(name, row["base"], row["best"], row["novel"], row["bits"], flush=True)
    return row

with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(job, jobs))
(directory / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
