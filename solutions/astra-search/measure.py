#!/usr/bin/env python3
"""指定64ケースを同じCPU・並列数で交互測定。stdoutは保存せず、stderrの数値をCSVに残す。"""
import argparse, concurrent.futures, csv, json, math, os, pathlib, re, statistics, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
TESTER = '/home/sato/ahc074/tools/target/release/tester'
p = argparse.ArgumentParser()
p.add_argument('label')
p.add_argument('binaries', nargs='+')
p.add_argument('--seeds', default='24-88')
p.add_argument('--sim', action='store_true')
p.add_argument('--jobs', type=int, default=3)
p.add_argument('--repeat', type=int, default=1)
p.add_argument('--fixed', type=int, default=0)
a = p.parse_args()
assert 1 <= a.jobs <= 4
seeds = list(range(*map(int, a.seeds.split('-')))) if '-' in a.seeds else list(map(int, a.seeds.split(',')))
out = HERE / (a.label + '.csv')
assert not out.exists(), out
env = os.environ.copy()
for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','SIM_SEQS']:
    env.pop(k, None)
if a.sim: env.update(SIM_SEQS='8', ANNEAL_ITERS='15500000', CLIMB_ITERS='66000')
if a.fixed: env.update(MAP_ITERS=str(a.fixed), GOPT_STEPS=str(a.fixed//4), ANNEAL_ITERS='1024', CLIMB_ITERS='-1')
cpus = sorted(os.sched_getaffinity(0))[:a.jobs]

def lane(slot):
    result = []
    for pos in range(slot, len(seeds), a.jobs):
        seed = seeds[pos]
        for rep in range(a.repeat):
            # 隣接seedで実行順を逆転。同じseedの両版は同じCPUで逐次実行。
            seq = a.binaries if (pos + rep) % 2 == 0 else a.binaries[::-1]
            for b in seq:
                binary = str((HERE / b).resolve())
                cmd = [binary] if a.sim else [TESTER, binary]
                cmd = ['taskset', '-c', str(cpus[slot])] + cmd
                t = time.monotonic()
                with (ROOT / 'tools/in' / f'{seed:04}.txt').open('rb') as f:
                    r = subprocess.run(cmd, stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, timeout=90)
                txt = r.stderr.decode()
                vals = {k: float(v) for k,v in re.findall(r'^([a-zA-Z_][a-zA-Z_0-9]*) = ([-+0-9.eE]+)$', txt, re.M)}
                row = dict(binary=b,seed=seed,rep=rep,cpu=cpus[slot],wall=time.monotonic()-t,returncode=r.returncode,**vals)
                if r.returncode or (not a.sim and vals.get('Score', 0) <= 0) or (a.sim and 'sim_moves' not in vals):
                    (HERE / f'{a.label}-error-{seed}-{pathlib.Path(b).name}.txt').write_text(txt)
                    raise RuntimeError(row)
                result.append(row)
        if (pos//a.jobs) % 4 == 0: print(f'lane={slot} seed={seed} done', flush=True)
    return result
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as ex:
    for result in ex.map(lane, range(a.jobs)): rows.extend(result)
rows.sort(key=lambda r:(r['seed'],r['rep'],r['binary']))
cols=list(dict.fromkeys(k for r in rows for k in r))
with out.open('w') as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
summary={'config':vars(a),'cpus':cpus,'variants':{},'compare':{}}
for b in a.binaries:
    rr=[r for r in rows if r['binary']==b]
    summary['variants'][b]={k:{'mean':statistics.mean(r[k] for r in rr if k in r),'max':max(r[k] for r in rr if k in r)} for k in cols[5:] if any(k in r for r in rr)}
base={(r['seed'],r['rep']):r for r in rows if r['binary']==a.binaries[0]}
for b in a.binaries[1:]:
    sr={}
    for metric in ['gobj_after','sim_moves','total_moves','map_iters','gopt_steps']:
        pp=[(r[metric],base[r['seed'],r['rep']][metric]) for r in rows if r['binary']==b and metric in r]
        if not pp: continue
        delta=[math.log(x/y)*100 for x,y in pp if x>0 and y>0]
        sr[metric]={'n':len(pp),'log_pct':statistics.mean(delta),'se_pct':statistics.stdev(delta)/math.sqrt(len(delta)) if len(delta)>1 else 0,'win':sum(x<y for x,y in pp),'tie':sum(x==y for x,y in pp),'loss':sum(x>y for x,y in pp),'delta':statistics.mean(x-y for x,y in pp)}
    summary['compare'][b]=sr
(HERE/(a.label+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary['compare'],indent=2))
print('means/max:', {b:{k:v for k,v in s.items() if k in ['gobj_after','end_sec','sim_moves','map_iters','gopt_steps']} for b,s in summary['variants'].items()})
