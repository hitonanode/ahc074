#!/usr/bin/env python3
"""このディレクトリ内だけへ記録する公式 tester / 設計模型の比較器。"""
import argparse, concurrent.futures as cf, hashlib, json, math, os, re, statistics, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
TESTER=Path('/home/sato/ahc074/tools/target/release/tester')
p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--bins',nargs='+',required=True,help='name=executable')
p.add_argument('--seeds',default='24:88')
p.add_argument('--threads',type=int,default=8)
p.add_argument('--model',action='store_true')
p.add_argument('--fixed',default='')
p.add_argument('--env',nargs='*',default=[])
a=p.parse_args(); start,end=map(int,a.seeds.split(':'))
bins=[(x.split('=',1)[0],Path(x.split('=',1)[1]).resolve()) for x in a.bins]
outdir=ROOT/'work'/a.label; outdir.mkdir(parents=True,exist_ok=True)
env=os.environ.copy(); env['DETAIL']='1'
if a.model:env.update(MODEL_ONLY='1',DUMP_DESIGN='1')
if a.fixed:
 for k,v in zip(['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS'],a.fixed.split(',')):env[k]=v
for x in a.env:
 k,v=x.split('=',1);env[k]=v
rx=re.compile(r'^([A-Za-z_][A-Za-z0-9_]*) = ([-+\deE.]+)$',re.M)
def run(job):
 seed,idx=job; name,binary=bins[idx]
 inp=Path('/home/sato/ahc074/tools/in')/f'{seed:04d}.txt'
 cmd=[str(binary)] if a.model else [str(TESTER),str(binary)]
 t=time.monotonic()
 with inp.open('rb') as f:
  r=subprocess.run(cmd,stdin=f,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=45)
 elapsed=time.monotonic()-t; err=r.stderr.decode(); st={k:float(v) for k,v in rx.findall(err)}
 (outdir/f'{name}-{seed:04d}.out').write_bytes(r.stdout)
 (outdir/f'{name}-{seed:04d}.err').write_text(err)
 return {'seed':seed,'name':name,'returncode':r.returncode,'wall_sec':elapsed,'stats':st}
# Adjacent jobs use opposite solver order on alternate seeds. Sixteen workers
# means eight matched seeds, each with the base and candidate at once.
jobs=[]
for seed in range(start,end):
 for idx in (list(range(len(bins))) if seed%2==0 else list(reversed(range(len(bins))))):jobs.append((seed,idx))
rows=[]; t=time.monotonic()
with cf.ThreadPoolExecutor(max_workers=a.threads) as pool:
 for r in pool.map(run,jobs):
  rows.append(r)
  if len(rows)%32==0:print(f'{a.label}: {len(rows)}/{len(jobs)}, {time.monotonic()-t:.1f}s',flush=True)
summ={}
for name,_ in bins:
 rs=[r for r in rows if r['name']==name]; keys=sorted(set().union(*(r['stats'] for r in rs)))
 summ[name]={'n':len(rs),'return_errors':sum(r['returncode']!=0 for r in rs),'mean':{},'max':{}}
 for k in keys:
  xs=[r['stats'][k] for r in rs if k in r['stats']]
  summ[name]['mean'][k]=statistics.mean(xs); summ[name]['max'][k]=max(xs)
 if not a.model:
  summ[name]['wa']=sum(r['stats'].get('Score',0)==0 for r in rs)
  summ[name]['wrong_cases']=sum(r['stats'].get('self_wrong',1)!=0 for r in rs)
base=bins[0][0]; paired={}
for name,_ in bins[1:]:
 b={r['seed']:r['stats'] for r in rows if r['name']==base};c={r['seed']:r['stats'] for r in rows if r['name']==name}
 key='model_cost' if a.model else 'Score'
 ds=[100*math.log(c[s][key]/b[s][key]) for s in b if b[s].get(key,0)>0 and c[s].get(key,0)>0]
 paired[name]={'n':len(ds),'log_ratio_percent':statistics.mean(ds),'se_percent':statistics.stdev(ds)/math.sqrt(len(ds)) if len(ds)>1 else 0,'wins':sum(x<0 for x in ds),'ties':sum(x==0 for x in ds),'losses':sum(x>0 for x in ds)}
 for key2 in ['model_cost','model_col','model_hole','model_gc','gobj_after','compatible_close','pair_shallow_hd','pair_generic_hd','pair_handle_hd','triangle_holes','pair_extra_holes','generic_moves','total_moves']:
  xs=[c[s][key2]-b[s][key2] for s in b if key2 in b[s] and key2 in c[s]]
  if xs:paired[name][key2+'_delta']={'mean':statistics.mean(xs),'se':statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else 0}
result={'label':a.label,'model':a.model,'seeds':[start,end],'threads':a.threads,'env':{k:env[k] for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','MODEL_ONLY','DETAIL','DUMP_DESIGN'] if k in env},'bins':{n:{'path':str(b),'sha256':hashlib.sha256(b.read_bytes()).hexdigest()} for n,b in bins},'summary':summ,'comparisons':paired,'cases':rows}
(ROOT/'results'/f'{a.label}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'label':a.label,'comparisons':paired,'summary':summ},ensure_ascii=False,indent=2),flush=True)
