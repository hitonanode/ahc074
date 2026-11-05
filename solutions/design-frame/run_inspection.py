"""Read saved designs under the evaluation lock; never run a solution/tester."""
import argparse, fcntl, json, statistics, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
import replay
p=argparse.ArgumentParser()
p.add_argument('--seeds',default='0-200')
p.add_argument('--run',default='20261105-080311_esw-speed')
p.add_argument('--moves',action='store_true')
p.add_argument('--output',default='inspection.json')
a=p.parse_args();lo,hi=map(int,a.seeds.split('-'));run=replay.resolve_run(a.run);rows=[]
with (replay.runs_dir()/'.lock').open('r') as lock:
 print('Waiting for analysis lock',flush=True);fcntl.flock(lock,fcntl.LOCK_SH)
 for seed in range(lo,hi):
  cmd=[str(HERE/'inspect'),str(replay.main_root()/'tools'/'in'/f'{seed:04d}.txt'),str(run/'design'),str(int(a.moves))]
  result=subprocess.run(cmd,check=True,capture_output=True,text=True)
  row={'seed':seed,**json.loads(result.stdout)};rows.append(row)
  print(seed,row['map_final_overlap'],row['cap_gain'],flush=True)
 fcntl.flock(lock,fcntl.LOCK_UN)
def stats(v):return {'mean':statistics.mean(v),'se':statistics.stdev(v)/len(v)**.5 if len(v)>1 else 0}
summary={k:stats([r[k] for r in rows]) for k,v in rows[0].items() if isinstance(v,(int,float)) and k!='seed'}
out={'run':run.name,'seeds':[lo,hi],'summary':summary,'rows':rows}
(HERE/a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(summary,indent=2))
