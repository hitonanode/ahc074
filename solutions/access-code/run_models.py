from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import json
import subprocess
import statistics
import math

folder=Path(__file__).resolve().parent/"sweep"
folder.mkdir(exist_ok=True)
def job(item):
    seed,bits=item;name=f"{seed:04d}-b{bits}"
    paths=[f"/home/sato/ahc074/tools/in/{seed:04d}.txt",f"/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04d}.txt"]
    with (folder/f"{name}-search.err").open("w") as log:
        p=subprocess.run(["/tmp/ahc074-access-search",*paths,"iters=2000000",f"maxbits={bits}","seconds=120","price=3.0"],capture_output=False,stdout=subprocess.PIPE,stderr=log,text=True,check=True)
    r=json.loads(p.stdout);r["seed"]=seed;(folder/f"{name}-search.json").write_text(json.dumps(r,indent=2)+"\n")
    env=os.environ.copy();env["ACCESS_SAVE_PREFIX"]=str(folder/name)
    with (folder/f"{name}-exact.err").open("w") as log:
        p=subprocess.run(["/tmp/ahc074-access-independent",*paths,*[str(r[k]) for k in ("mask0","color0","mask1","color1")],"2"],env=env,stdout=subprocess.PIPE,stderr=log,text=True,check=True)
    exact=json.loads(p.stdout);exact["seed"]=seed;exact["maxbits"]=bits
    (folder/f"{name}-exact.json").write_text(json.dumps(exact,indent=2)+"\n")
    print(seed,bits,[round(x.get("cost",0),5) for x in exact["models"]],flush=True)
    return exact
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,[(s,b) for s in range(24,32) for b in (8,14,20)]))
(folder/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
def stationary(seed):
    rows_seed=[r for r in rows if r["seed"]==seed]
    best=min(rows_seed,key=lambda r:r["models"][2]["cost"]);name=f"{seed:04d}-b{best['maxbits']}"
    with (folder/f"{name}-mdp.err").open("w") as log:
        p=subprocess.run(["/tmp/ahc074-generic-mdp",str(folder/f"{name}-2.in"),str(folder/f"{name}-2.out"),"8","2"],stdout=subprocess.PIPE,stderr=log,text=True,check=True)
    mdp=json.loads(p.stdout);m=best["models"][2];mdp["seed"]=seed;mdp["maxbits"]=best["maxbits"]
    mdp["corrected_cost"]=m["column"]+m["holes"]+mdp["optimal_lo"]*mdp["targets"]/256
    mdp["base_cost"]=best["models"][0]["cost"];mdp["difference"]=mdp["corrected_cost"]-mdp["base_cost"]
    (folder/f"{name}-mdp.json").write_text(json.dumps(mdp,indent=2)+"\n")
    print("mdp",seed,mdp["difference"],flush=True);return mdp
with ThreadPoolExecutor(max_workers=4) as pool:
    final=list(pool.map(stationary,range(24,32)))
(folder/"stationary-summary.json").write_text(json.dumps(final,indent=2)+"\n")
a=[r["difference"] for r in final]
print("corrected difference",statistics.mean(a),statistics.stdev(a)/math.sqrt(len(a)),flush=True)
