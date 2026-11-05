"""Inspect a harmed case and operation labels from already recorded outputs."""
import subprocess
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import replay

base='20261106-061252_argon-des-perf-rematch-v2'
cand='20261106-061252_argon-des-perf-latew70'
seed=66
inp=replay.load_input(seed)
outs=[replay.parse_output(inp,(replay.runs_dir()/run/'out'/f'{seed:04d}.txt').read_text()) for run in [base,cand]]
worst=sorted(range(1024),key=lambda r:len(outs[1].queries[r])-len(outs[0].queries[r]),reverse=True)[:3]
commands=[['cases',cand,'--vs',base,'--top','8'],
          ['stats',cand,'--vs',base,'--seed',str(seed),'--attr','role,col']]
for r in worst:
    for run in [base,cand]:
        commands.append(['queries',run,str(seed),'--from',str(r),'--to',str(r+1),'--attr','role,col'])
for run in [base,cand]:
    commands.append(['state',run,str(seed),'--request',str(worst[0]),'--top','12'])
with (HERE/'observe-lower.log').open('w') as out:
    out.write(f'seed={seed}; largest per-request increases={worst}\n')
    out.flush()
    for args in commands:
        out.write('\nobserve.py '+' '.join(args)+'\n'); out.flush()
        subprocess.run([sys.executable,str(ROOT/'scripts/observe.py'),*args],stdout=out,stderr=subprocess.STDOUT,check=True)
print('saved observe-lower.log',worst)
