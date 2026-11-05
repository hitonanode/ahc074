"""Inspect the first changed plan in a harmful saved case; no solution execution."""
import subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay
base='20261106-022157_argon-des-perf-gaincache';candidate='20261106-022157_argon-des-perf-donorhole';seed=383
inp=replay.load_input(seed)
outs=[replay.parse_output(inp,(Path('/home/sato/ahc074/runs')/run/'out'/f'{seed:04d}.txt').read_text())for run in [base,candidate]]
q=next(i for i,(a,b)in enumerate(zip(outs[0].queries,outs[1].queries))if a!=b)
print('seed',seed,'first_changed_query',q,'target',inp.requests[q],flush=True)
for run in [base,candidate]:
    subprocess.run(['python3','scripts/observe.py','queries',run,str(seed),'--from',str(q),'--to',str(q+2),'--attr','role,col'],check=True)
    subprocess.run(['python3','scripts/observe.py','state',run,str(seed),'--request',str(q),'--after'],check=True)
