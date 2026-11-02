#!/usr/bin/env python3
"""基準と候補を8個ずつ同時に走らせ、隣のバッチで起動順を反転する。"""
import argparse, concurrent.futures, csv, json, math, os, pathlib, re, statistics, subprocess, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TESTER='/home/sato/ahc074/tools/target/release/tester'
p=argparse.ArgumentParser()
p.add_argument('label');p.add_argument('base');p.add_argument('candidate')
p.add_argument('--sim',action='store_true');p.add_argument('--seeds',default='24-88')
p.add_argument('--fixed',type=int,default=0);p.add_argument('--pairs',type=int,default=8)
p.add_argument('--direct',action='store_true',help='入力を直接与える診断用。公式検証は別途行う')
a=p.parse_args();assert 1<=a.pairs<=8
seeds=list(range(*map(int,a.seeds.split('-'))))
out=HERE/(a.label+'.csv');assert not out.exists(),out
env=os.environ.copy()
for k in ('MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','SIM_SEQS'):env.pop(k,None)
if a.sim:env.update(SIM_SEQS='8',ANNEAL_ITERS='20000000',CLIMB_ITERS='66000')
if a.fixed:env.update(MAP_ITERS=str(a.fixed),GOPT_STEPS=str(a.fixed//4),ANNEAL_ITERS='1024',CLIMB_ITERS='-1')

def run(task):
    seed,b,slot=task
    cmd=[str(HERE/b)]
    if not (a.sim or a.direct):cmd=[TESTER]+cmd
    started=time.time()
    with (ROOT/'tools/in'/f'{seed:04}.txt').open('rb') as f:
        r=subprocess.run(cmd,stdin=f,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env,timeout=120)
    txt=r.stderr.decode()
    vals={k:float(v) for k,v in re.findall(r'^([a-zA-Z_][a-zA-Z_0-9]*) = ([-+0-9.eE]+)$',txt,re.M)}
    row=dict(binary=b,seed=seed,slot=slot,started=started,wall=time.time()-started,returncode=r.returncode,**vals)
    bad=r.returncode or (a.sim and 'sim_moves' not in vals) or (not (a.sim or a.direct) and vals.get('Score',0)<=0)
    if bad:
        (HERE/f'{a.label}-error-{seed}-{b}.txt').write_text(txt)
        raise RuntimeError(row)
    return row
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2*a.pairs) as pool:
    for batch,start in enumerate(range(0,len(seeds),a.pairs)):
        tasks=[]
        for offset,seed in enumerate(seeds[start:start+a.pairs]):
            seq=[a.base,a.candidate]
            if (offset+batch)%2:seq.reverse()
            for b in seq:tasks.append((seed,b,len(tasks)))
        rows.extend(pool.map(run,tasks))
        print('batch',batch,'completed',len(rows),'runs',flush=True)
rows.sort(key=lambda r:(r['seed'],r['binary']))
cols=list(dict.fromkeys(k for r in rows for k in r))
with out.open('w') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
summary={'config':vars(a),'variants':{},'compare':{}}
for b in (a.base,a.candidate):
    rr=[r for r in rows if r['binary']==b]
    summary['variants'][b]={k:{'mean':statistics.mean(r[k] for r in rr if k in r),'min':min(r[k] for r in rr if k in r),'max':max(r[k] for r in rr if k in r)} for k in cols[6:] if any(k in r for r in rr)}
base={r['seed']:r for r in rows if r['binary']==a.base}
for metric in ('gobj_after','sim_moves','total_moves','map_iters','gopt_steps','search_exact_evals'):
    pp=[(r[metric],base[r['seed']][metric]) for r in rows if r['binary']==a.candidate and metric in r]
    if not pp:continue
    dd=[100*math.log(x/y) for x,y in pp if x>0 and y>0]
    summary['compare'][metric]={'n':len(pp),'log_pct':statistics.mean(dd),'se_pct':statistics.stdev(dd)/math.sqrt(len(dd)) if len(dd)>1 else 0,'win':sum(x<y for x,y in pp),'tie':sum(x==y for x,y in pp),'loss':sum(x>y for x,y in pp)}
(HERE/(a.label+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary['compare'],indent=2))
print('means/max',json.dumps({b:{k:v for k,v in d.items() if k in ('gobj_after','sim_moves','end_sec','search_exact_evals','map_iters','priority_misses','priority_hits','transfer_rows')} for b,d in summary['variants'].items()}))
