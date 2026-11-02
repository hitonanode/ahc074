#!/usr/bin/env python3
"""研究用方策を公式テスターで逐次検査。最大tester+solverの2子プロセス。"""
from pathlib import Path
import argparse, json, os, re, subprocess, time
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--binary',default='fast3')
p.add_argument('--seeds',default='24:28')
p.add_argument('--samples',type=int,default=128)
p.add_argument('--expand',type=int,default=1)
p.add_argument('--keep',type=int,default=2)
a=p.parse_args()
out=ROOT/'results'/a.label
out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(MAP_ITERS='380000',GOPT_STEPS='110000',ANNEAL_ITERS='19000000',CLIMB_ITERS='65000',
           SIM_SEQS='0',ORACLE_SAMPLES=str(a.samples),EXPAND=str(a.expand),EXPAND_SCREEN='8',EXPAND_KEEP=str(a.keep))
lo,hi=map(int,a.seeds.split(':'))
rows=[]
for seed in range(lo,hi):
    start=time.monotonic()
    with (Path('/home/sato/ahc074/tools/in')/f'{seed:04d}.txt').open('rb') as inp, (out/f'{seed:04d}.out').open('wb') as stdout, (out/f'{seed:04d}.err').open('wb') as stderr:
        r=subprocess.run(['/home/sato/ahc074/tools/target/release/tester',str(ROOT/a.binary)],stdin=inp,stdout=stdout,stderr=stderr,env=env,timeout=1200)
    err=(out/f'{seed:04d}.err').read_text()
    stats={k:float(v) for k,v in re.findall(r'^([A-Za-z_][A-Za-z0-9_]*) = ([-+\deE.]+)$',err,re.M)}
    row={'seed':seed,'returncode':r.returncode,'stats':stats,'wall_sec':time.monotonic()-start}
    rows.append(row)
    (out/'summary.json').write_text(json.dumps({'config':vars(a),'cases':rows},indent=2)+'\n')
    print(json.dumps(row),flush=True)
    assert r.returncode==0 and stats.get('Score',0)>0 and stats.get('self_wrong',1)==0
