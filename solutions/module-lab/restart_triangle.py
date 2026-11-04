from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory=Path(__file__).resolve().parent/"triangle-restarts"
directory.mkdir(exist_ok=True)
def job(seed):
    path=directory/f"{seed}.json"
    command=["/tmp/ahc074-module-v3","K=7","q=0.1","seed=3",f"search_seed={seed}",
             "triangle=1","iters=1000","seconds=150"]
    with (directory/f"{seed}.err").open("w") as log:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=300)
    row=json.loads(result.stdout);row["search_seed"]=seed
    path.write_text(json.dumps(row,indent=2)+"\n")
    print(seed,row["best"],flush=True)
    return row
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(job,range(10,16)))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
