from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

directory=Path(__file__).resolve().parent/"general-results"
directory.mkdir(exist_ok=True)
jobs=[(q,seed,mode) for q in (.05,.2) for seed in range(1,5) for mode in ("triangle","body","free")]
def job(item):
    q,seed,mode=item
    name=f"q{int(q*100):02d}-s{seed}-{mode}"
    path=directory/f"{name}.json"
    if path.exists():return json.loads(path.read_text())
    command=["/tmp/ahc074-overlap-general","G=3","M=3","H=2","K=7",f"q={q}",f"seed={seed}",
             f"triangle={int(mode=='triangle')}","lock_generic=1",f"lock_body={int(mode=='body')}",
             "gprob=0.5","iters=2000","seconds=300"]
    with (directory/f"{name}.err").open("w") as log:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=480)
    row=json.loads(result.stdout)
    path.write_text(json.dumps(row,indent=2)+"\n")
    print(name,row["baseline"],row["best"],row["opaque"],row["black"],flush=True)
    return row
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,jobs))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
