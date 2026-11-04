from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"scripts"))
import replay

directory=Path(__file__).resolve().parent/"profiles"
directory.mkdir(exist_ok=True)
run=replay.resolve_run("20261103-033246_as6-canon")
jobs=[]
for seed in range(24,32):
    inp=replay.load_input(seed)
    out=replay.parse_output(inp,(run/"out"/f"{seed:04d}.txt").read_text())
    papers=out.designs
    cap=papers[0].opaque
    generic=0
    for paper in papers[1:7]:generic|=paper.opaque
    handle=((1<<64)-1)^(generic|cap)
    columns=[]
    for paper in papers[7:]:
        for j in range(64):
            if handle>>j&1 and paper.opaque>>j&1 and j not in columns:columns.append(j)
    counts=[[0]*4 for _ in columns]
    holes=[[0,0] for _ in columns]
    for paper in papers[7:]:
        owners=[a for a,target in enumerate(inp.target) if not ((target^paper.black)&paper.opaque&~cap)]
        assert len(owners) in (1,2)
        c=max(i for i,j in enumerate(columns) if paper.opaque>>j&1)
        kind=(paper.black>>columns[c]&1)+2*(len(owners)-1)
        counts[c][kind]+=1
        for i,j in enumerate(columns):
            if paper.opaque>>j&1:continue
            for a in owners:holes[i][inp.target[a]>>j&1]+=1
    for c,(count,(r0,r1)) in enumerate(zip(counts,holes)):
        states=math.factorial(sum(count))//math.prod(math.factorial(x) for x in count)
        jobs.append(dict(seed=seed,column=c,counts=count,r0=r0,r1=r1,states=states))

def job(record):
    path=directory/f"{record['seed']:04d}-{record['column']:02d}.json"
    if path.exists():return json.loads(path.read_text())
    if record["states"]>100000:
        record["skipped"]=True
    else:
        command=["/tmp/ahc074-queue","counts="+",".join(map(str,record["counts"])),f"r0={record['r0']}",f"r1={record['r1']}"]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True,timeout=180)
        record.update(json.loads(result.stdout));record["skipped"]=False
    path.write_text(json.dumps(record,indent=2)+"\n")
    return record
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(job,jobs))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
for seed in range(24,32):
    a=[r for r in rows if r["seed"]==seed]
    print(seed,"gain",sum(r.get("global_difference",0) for r in a),"skipped",sum(r["skipped"] for r in a),flush=True)
