"""基準・候補を seed ごとに順番を交替させ、公式テスターで測る。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics as st
import subprocess
import time

HERE=Path(__file__).resolve().parent
TESTER='/home/sato/ahc074/tools/target/release/tester'
INPUT=Path('/home/sato/ahc074/tools/in')
p=argparse.ArgumentParser()
p.add_argument('name');p.add_argument('binaries',nargs='+')
p.add_argument('--from-seed',type=int,default=24);p.add_argument('--to-seed',type=int,default=88)
p.add_argument('--jobs',type=int,default=6)
a=p.parse_args();assert 1<=a.jobs<=6
dest=HERE/'data'/a.name;dest.mkdir(parents=True,exist_ok=True)
bins=[Path(b).resolve() for b in a.binaries]
env=dict(os.environ)
for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','SIM_SEQS','MAP_SEED']:
    env.pop(k,None)
(dest/'config.json').write_text(json.dumps(dict(args=vars(a),tester=TESTER,
    sha256={b.name:hashlib.sha256(b.read_bytes()).hexdigest() for b in bins}),indent=2))

def run(seed):
    results={}
    order=list(range(len(bins)))
    order=order[seed%len(bins):]+order[:seed%len(bins)]
    for idx in order:
        b=bins[idx];start=time.monotonic()
        with (INPUT/f'{seed:04d}.txt').open() as f:
            r=subprocess.run([TESTER,str(b)],stdin=f,stdout=subprocess.DEVNULL,
                             stderr=subprocess.PIPE,text=True,env=env,timeout=30)
        (dest/f'{seed:04d}-{idx}.err').write_text(r.stderr)
        stats={}
        for l in r.stderr.splitlines():
            m=re.fullmatch(r'([A-Za-z_0-9]+) = ([-+.0-9eE]+)',l)
            if m:stats[m[1]]=float(m[2])
        score=stats.get('Score',0)
        e=(score-stats.get('total_moves',math.inf))/384
        results[str(idx)]=dict(binary=b.name,returncode=r.returncode,elapsed=time.monotonic()-start,
                               stats=stats,score=score,E=e)
    out=dict(seed=seed,order=order,results=results)
    (dest/f'{seed:04d}.json').write_text(json.dumps(out))
    return out

start=time.monotonic();rows=[]
with ThreadPoolExecutor(a.jobs) as ex:
    for i,r in enumerate(ex.map(run,range(a.from_seed,a.to_seed)),1):
        rows.append(r)
        if i%16==0:print(a.name,i,'cases',round(time.monotonic()-start,1),'s',flush=True)

def avgse(xs):return st.mean(xs),st.stdev(xs)/len(xs)**.5
report=[]
for idx,b in enumerate(bins):
    rs=[r['results'][str(idx)] for r in rows]
    valid=[r for r in rs if r['score']>0 and r['returncode']==0]
    report.append(f'{b.name}: n={len(rs)} WA={len(rs)-len(valid)} E={sum(r["E"] for r in rs)} '
                  f'fast_requests={sum(r["stats"].get("fast_requests",0) for r in rs)} '
                  f'end_sec_max={max(r["stats"].get("end_sec",math.inf) for r in rs):.6f}')
    if idx:
        good=[r for r in rows if r['results']['0']['score']>0 and r['results'][str(idx)]['score']>0]
        dif=[100*math.log(r['results'][str(idx)]['score']/r['results']['0']['score']) for r in good]
        report.append(f'  log ratio={avgse(dif)[0]:+.6f} ± {avgse(dif)[1]:.6f}% '
                      f'W/D/L={sum(d<0 for d in dif)}/{sum(d==0 for d in dif)}/{sum(d>0 for d in dif)}')
    for k in ['Score','model_cost','model_col','model_hole','model_gc','map_iters','gopt_steps','search_exact_evals','anneal_iters','end_sec','req_sec']:
        xs=[r['stats'][k] for r in valid if k in r['stats']]
        if xs:report.append(f'  {k}={avgse(xs)[0]:.6f} ± {avgse(xs)[1]:.6f}')
text='\n'.join(report)+'\n';print(text);(dest/'summary.txt').write_text(text)
