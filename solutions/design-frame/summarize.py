"""Scores, paired timing differences and exact-output checks for recorded runs."""
import argparse,fcntl,json,math,re,statistics,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
import replay
p=argparse.ArgumentParser()
p.add_argument('runs',nargs='+')
p.add_argument('--seeds',default='0-200')
p.add_argument('--identity',action='store_true')
p.add_argument('--output',default='summary.json')
a=p.parse_args();lo,hi=map(int,a.seeds.split('-'))
runs=[replay.resolve_run(s) for s in a.runs]
metric=re.compile(r'^([A-Za-z_][\w]*) = ([+-]?[\d.]+(?:e[+-]?\d+)?)$',re.M)
def stats(v):return {'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0}
def load(run):
 return [dict((m[0],float(m[1])) for m in metric.findall((run/'err'/f'{s:04d}.txt').read_text()))for s in range(lo,hi)]
def stable(text):return '\n'.join(l for l in text.splitlines() if not re.match(r'^\w*sec\s*=',l))
with (replay.runs_dir()/'.lock').open('r') as lock:
 fcntl.flock(lock,fcntl.LOCK_SH)
 rows=[load(r) for r in runs];base=rows[0];out=[]
 for run,data in zip(runs,rows):
  ratios=[100*math.log(r['Score']/b['Score'])for r,b in zip(data,base) if r['Score']>0 and b['Score']>0]
  item={'run':run.name,'n':len(data),'score_log_percent':stats(ratios),
        'wins':sum(r['Score']<b['Score'] for r,b in zip(data,base)),
        'ties':sum(r['Score']==b['Score'] for r,b in zip(data,base)),
        'losses':sum(r['Score']>b['Score'] for r,b in zip(data,base)),'metrics':{}}
  for key in ['map_end_sec','anneal_end_sec','match_sec','helper_end_sec','req_sec','end_sec','model_cost','model_col','model_hole','model_gc','proxy_after','match_decrease','frame_cap_sec','frame_cap_gain','frame_mid_sec']:
   if all(key in r for r in data):
    item['metrics'][key]=stats([r[key]for r in data])
    if all(key in b for b in base):item['metrics'][key]['delta']=stats([r[key]-b[key]for r,b in zip(data,base)])
  item['end_over']={str(t):sum(r['end_sec']>t for r in data)for t in [1.8,1.9,2.0]}
  if a.identity:
   item['stdout_identical']=sum((run/'out'/f'{s:04d}.txt').read_bytes()==(runs[0]/'out'/f'{s:04d}.txt').read_bytes()for s in range(lo,hi))
   item['stderr_nontime_identical']=sum(stable((run/'err'/f'{s:04d}.txt').read_text())==stable((runs[0]/'err'/f'{s:04d}.txt').read_text())for s in range(lo,hi))
  out.append(item)
 fcntl.flock(lock,fcntl.LOCK_UN)
result={'seeds':[lo,hi],'results':out}
(HERE/a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
