from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import statistics
import math

root=Path(__file__).resolve().parents[2]
folder=Path(__file__).resolve().parent/"results"
folder.mkdir(exist_ok=True)
def job(item):
    m,seed=item
    run="as6-canon" if m==6 else "eight-code"
    command=["/tmp/ahc074-generic-mdp",f"/home/sato/ahc074/tools/in/{seed:04d}.txt",f"/home/sato/ahc074/runs/20261103-092306_{run}/out/{seed:04d}.txt",str(m),"2"]
    p=subprocess.run(command,capture_output=True,text=True,check=True)
    row=json.loads(p.stdout);row["seed"]=seed
    (folder/f"{m}-{seed:04d}.json").write_text(json.dumps(row,indent=2)+"\n")
    return row
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,[(m,seed) for m in (6,8) for seed in range(24,32)]))
(folder/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
for m in (6,8):
    rr=[r for r in rows if r["M"]==m]
    for key in ("uniform","policy_lo","optimal_lo","global_gain"):
        a=[r[key] for r in rr]
        print(m,key,statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
