from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import json

folder=Path(__file__).resolve().parent
source=json.loads((folder/"results/0025-22.json").read_text())
changes=[i for i,(a,b) in enumerate(zip(source["original"],source["opaque"])) if a!=b]
directory=folder/"ablation";directory.mkdir(exist_ok=True)
def job(item):
    mask,width=item
    op=source["original"][:]
    for b,i in enumerate(changes):
        if mask>>b&1:op[i]=source["opaque"][i]
    command=["/tmp/ahc074-long-module",str(folder/"profiles/0025-22.txt"),"0","256","32768",str(width),",".join(map(str,op)),"300000007"]
    p=subprocess.run(command,capture_output=True,text=True,check=True)
    r=json.loads(p.stdout);r["mask"]=mask;r["width"]=width
    (directory/f"m{mask}-w{width}.json").write_text(json.dumps(r,indent=2)+"\n")
    print(mask,width,r["difference"],r["baseline_validation"],r["validation"],flush=True)
    return r
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,[(mask,width) for mask in range(8) for width in (4,8,16)]))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
