#!/usr/bin/env python3
"""少数並列の検査用。12並列の比較には measure_calls.js を使う。

Pythonと起動シェルの分を空け、通常版は最大10、公式テスターは最大5並列。
"""
import argparse, concurrent.futures, csv, json, math, os, pathlib, re, statistics, subprocess, time
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
p=argparse.ArgumentParser()
p.add_argument('label');p.add_argument('binaries',nargs='+')
p.add_argument('--seeds',default='24-88');p.add_argument('--sim',action='store_true')
p.add_argument('--tester',action='store_true');p.add_argument('--jobs',type=int,default=5)
a=p.parse_args()
assert 1<=a.jobs<=10
if a.tester: assert a.jobs<=5
seeds=list(range(*map(int,a.seeds.split('-'))))
out=H/(a.label+'.csv');assert not out.exists()
env=os.environ.copy()
for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','SIM_SEQS']: env.pop(k,None)
if a.sim: env.update(SIM_SEQS='8',MAP_ITERS='1110000',GOPT_STEPS='353500',CLIMB_ITERS='66500')
# 固定しない。P/Eコアの差を含む同一負荷で基準・候補を交互に動かす。
def lane(slot):
    rows=[]
    for pos in range(slot,len(seeds),a.jobs):
        seed=seeds[pos]
        shift=pos%len(a.binaries)
        order=a.binaries[shift:]+a.binaries[:shift]
        if (pos//len(a.binaries))%2: order=order[::-1]
        for b in order:
            cmd=[str(H/b)]
            if a.tester: cmd=['/home/sato/ahc074/tools/target/release/tester']+cmd
            start=time.monotonic()
            with (ROOT/'tools/in'/f'{seed:04}.txt').open('rb') as f:
                r=subprocess.run(cmd,stdin=f,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env,timeout=90)
            txt=r.stderr.decode()
            vals={k:float(v) for k,v in re.findall(r'^([A-Za-z_][A-Za-z_0-9]*) = ([-+0-9.eE]+)$',txt,re.M)}
            row=dict(binary=b,seed=seed,lane=slot,wall=time.monotonic()-start,returncode=r.returncode,**vals)
            required='sim_moves' if a.sim else 'end_sec'
            if r.returncode or required not in vals or (a.tester and vals.get('Score',0)<=0):
                (H/f'{a.label}-error-{seed}-{b}.txt').write_text(txt)
                raise RuntimeError(row)
            rows.append(row)
        print(f'seed {seed} done',flush=True)
    return rows
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as ex:
    for rr in ex.map(lane,range(a.jobs)): rows.extend(rr)
rows.sort(key=lambda r:(r['seed'],r['binary']))
cols=list(dict.fromkeys(k for r in rows for k in r))
with out.open('w') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
s={'config':vars(a),'variants':{},'compare':{}}
for b in a.binaries:
    rr=[r for r in rows if r['binary']==b]
    s['variants'][b]={k:{'mean':statistics.mean(r[k] for r in rr if k in r),'min':min(r[k] for r in rr if k in r),'max':max(r[k] for r in rr if k in r)} for k in cols if k not in ['binary','seed','lane'] and any(k in r for r in rr)}
base={r['seed']:r for r in rows if r['binary']==a.binaries[0]}
for b in a.binaries[1:]:
    sr={}
    for m in ['anneal_cost','sim_moves','total_moves','anneal_iters','gobj_after']:
        pairs=[(r[m],base[r['seed']][m]) for r in rows if r['binary']==b and m in r]
        if not pairs: continue
        dd=[100*math.log(x/y) for x,y in pairs if x>0 and y>0]
        sr[m]=dict(n=len(pairs),log_pct=statistics.mean(dd),se_pct=statistics.stdev(dd)/math.sqrt(len(dd)),win=sum(x<y for x,y in pairs),tie=sum(x==y for x,y in pairs),loss=sum(x>y for x,y in pairs),delta=statistics.mean(x-y for x,y in pairs))
    s['compare'][b]=sr
(H/(a.label+'.json')).write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(s['compare'],indent=2))
print('means/max:',{b:{k:v for k,v in v.items() if k in ['anneal_cost','anneal_iters','sim_moves','end_sec','map_end_sec','sim_helper_papers']} for b,v in s['variants'].items()})
