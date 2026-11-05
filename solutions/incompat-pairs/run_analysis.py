"""Analyze saved designs/output while excluding live evaluations with their lock."""
import argparse
import fcntl
import json
from pathlib import Path
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import replay

p = argparse.ArgumentParser()
p.add_argument('--run', default='20261105-084037_esw-clean')
p.add_argument('--design-run', default='20261105-080311_esw-speed')
p.add_argument('--seeds', default='0-64')
p.add_argument('--model-iters', type=int, default=0)
p.add_argument('--output', default='counts.json')
a = p.parse_args()
run = replay.resolve_run(a.run)
design = replay.resolve_run(a.design_run)
lo, hi = map(int,a.seeds.split('-'))
rows = []
with (replay.runs_dir()/'.lock').open('r') as lock:
    print('Waiting for shared analysis lock (excludes evaluations)',flush=True)
    fcntl.flock(lock,fcntl.LOCK_SH)
    for seed in range(lo,hi):
        cmd = [str(HERE/'analyze'),str(replay.main_root()/'tools'/'in'/f'{seed:04d}.txt'),
               str(design/'design'),str(run/'out'/f'{seed:04d}.txt'),str(a.model_iters)]
        res = subprocess.run(cmd,check=True,capture_output=True,text=True)
        row = {'seed':seed,**json.loads(res.stdout)}
        rows.append(row)
        print(f'seed {seed}: near={row["stats"]["near"]:.0f}, one={row["errors_hist"][1]}, rescued={row["stats"].get("rescuable",0):.0f}',flush=True)
    fcntl.flock(lock,fcntl.LOCK_UN)

def summary(v):
    return {'mean':statistics.mean(v),'se':statistics.stdev(v)/len(v)**.5 if len(v)>1 else 0}
keys = sorted(set().union(*(row['stats'].keys() for row in rows)))
stats = {k:summary([row['stats'].get(k,0) for row in rows]) for k in keys}
hist = [summary([row['errors_hist'][j] for row in rows]) for j in range(39)]
models = []
if rows and rows[0]['models']:
    for i,m in enumerate(rows[0]['models']):
        models.append({'mode':i,'allowed':m['allowed'],'fee':m['fee'],
                       **{k:summary([row['models'][i][k] for row in rows]) for k in ['model','col','hole','generic','selected']},
                       'delta':summary([row['models'][i]['model']-row['models'][0]['model'] for row in rows])})
result = {'run':run.name,'design_run':design.name,'seeds':[lo,hi],'model_iters':a.model_iters,
          'stats':stats,'errors_hist':hist,'models':models,'rows':rows}
(HERE/a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'stats':stats,'errors_hist':hist[:8],'models':models},ensure_ascii=False,indent=2))
