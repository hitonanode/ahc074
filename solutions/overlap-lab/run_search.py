from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory=Path(__file__).resolve().parent/"results"
directory.mkdir(exist_ok=True)
jobs=[(q,seed,triangle) for q in (.05,.2,.5) for seed in range(1,5) for triangle in (1,0)]
def job(item):
    q,seed,triangle=item
    name=f"q{int(q*100):02d}-s{seed}-t{triangle}"
    path=directory/f"{name}.json"
    if path.exists():return json.loads(path.read_text())
    command=["/tmp/ahc074-overlap-module","H=2","K=6",f"q={q}",f"seed={seed}",
             f"triangle={triangle}","gprob=0.5","iters=6000","seconds=120"]
    with (directory/f"{name}.err").open("w") as log:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=240)
    row=json.loads(result.stdout)
    path.write_text(json.dumps(row,indent=2)+"\n")
    print(name,row["baseline"],row["best"],row["opaque"],row["black"],flush=True)
    return row
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,jobs))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
