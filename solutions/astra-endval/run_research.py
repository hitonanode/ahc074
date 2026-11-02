#!/usr/bin/env python3
"""指定ディレクトリ内にだけ書く模擬実験。最大13 solver + この1プロセス。"""
import argparse, concurrent.futures as cf, json, math, os, statistics, subprocess, time, threading
from pathlib import Path

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--seeds',default='24:88')
p.add_argument('--samples',type=int,default=0)
p.add_argument('--terminal',type=float,default=1)
p.add_argument('--seqs',type=int,default=4)
p.add_argument('--steps',type=int,default=1024)
p.add_argument('--jobs',type=int,default=12)
p.add_argument('--binary',default='research')
p.add_argument('--slots-file',default='')
p.add_argument('--env',nargs='*',default=[])
p.add_argument('--fixed',default='380000,110000,19000000,65000')
a=p.parse_args()
assert 1<=a.jobs<=13
lo,hi=map(int,a.seeds.split(':'))
out=ROOT/'results'/a.label
out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(dict(zip(['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS'],a.fixed.split(','))))
env.update(SIM_SEQS=str(a.seqs),SIM_STEPS=str(a.steps),ORACLE_SAMPLES=str(a.samples),TERMINAL_WEIGHT=str(a.terminal))
env.update(x.split('=',1) for x in a.env)
(out/'config.json').write_text(json.dumps(vars(a),indent=2)+'\n')
start=time.monotonic()
slot_lock=threading.Condition()
active=0
def run(seed):
    global active
    dest=out/f'{seed:04d}.jsonl'
    if dest.exists() and len(dest.read_text().splitlines())==a.seqs+1:
        return seed,'cached'
    with slot_lock:
        while a.slots_file:
            setting=(ROOT/a.slots_file).read_text().strip()
            if setting=='STOP':
                return seed,'stopped-before-start'
            if active < max(0,min(a.jobs,int(setting))):break
            slot_lock.wait(timeout=2)
        active+=1
    try:
        with (Path('/home/sato/ahc074/tools/in')/f'{seed:04d}.txt').open('rb') as inp, dest.open('w') as stdout, (out/f'{seed:04d}.err').open('w') as err:
            r=subprocess.run([str(ROOT/a.binary)],stdin=inp,stdout=stdout,stderr=err,env=env,timeout=5000)
    finally:
        with slot_lock:
            active-=1
            slot_lock.notify_all()
    return seed,r.returncode
with cf.ThreadPoolExecutor(max_workers=a.jobs) as pool:
    fs={pool.submit(run,s):s for s in range(lo,hi)}
    for f in cf.as_completed(fs):
        seed,ret=f.result()
        print(f'{a.label}: seed={seed} return={ret} elapsed={time.monotonic()-start:.1f}s',flush=True)
