from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import json

folder=Path(__file__).resolve().parent
def job(item):
    seed,start=item;name=f"{seed:04d}-{start}"
    profile=folder/"profiles"/f"{name}.txt"
    with profile.open("w") as f:subprocess.run(["python3",str(folder/"profile.py"),str(seed),str(start)],stdout=f,check=True)
    with (folder/"results"/f"{name}.err").open("w") as log:
        p=subprocess.run(["/tmp/ahc074-long-module",str(profile),"1500","4096","16384","4"],stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=3600)
    r=json.loads(p.stdout);r["seed"]=seed;r["column"]=start
    (folder/"results"/f"{name}.json").write_text(json.dumps(r,indent=2)+"\n")
    print(seed,start,r["difference"],r["best_train"]-r["baseline_train"],r["elapsed"],flush=True)
    return r
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,[(s,c) for s in range(24,28) for c in (19,22)]))
(folder/"results"/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
