from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import json
import statistics
import math

folder=Path(__file__).resolve().parent
def job(item):
    mode,seed=item
    directory=folder/("copies" if mode=="copy" else "direct")
    directory.mkdir(exist_ok=True)
    output=directory/f"{seed:04d}.json"
    command=["/tmp/ahc074-copy-probe" if mode=="copy" else "/tmp/ahc074-cover-probe",f"/home/sato/ahc074/tools/in/{seed:04d}.txt",f"/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt","24" if mode=="copy" else "10"]
    with (directory/f"{seed:04d}.err").open("w") as log:
        p=subprocess.run(command,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    r=json.loads(p.stdout);r["seed"]=seed;r["mode"]=mode
    output.write_text(json.dumps(r,indent=2)+"\n")
    print(mode,seed,{k:r[k] for k in ("difference","copy_gain") if k in r},flush=True)
    return r
jobs=[("copy",s) for s in range(24,32)]+[("direct",s) for s in range(24,28)]
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,jobs))
(folder/"model-summary.json").write_text(json.dumps(rows,indent=2)+"\n")
for key in ("difference","copy_gain"):
    a=[r[key] for r in rows if key in r]
    print(key,statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
