"""Compare identical-base timings with paired candidates and saved baseline timings."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
names=['20261106-022300_argon-req-completefast-v3','20261106-025319_argon-req-completefast-v3','20261106-030225_argon-req-completefast-v3','20261106-030615_argon-des-perf-stratafast']
rows=[]
for name in names:
    cases=json.loads((R/name/'metrics.json').read_text())['cases'];v={s:c['stderr']['end_sec']+.04*c['stderr']['helper_end_sec']+.35*c['stderr']['req_sec']for s,c in cases.items()}
    worst=sorted(v,key=v.get,reverse=True)[:40]
    row=dict(run=name,mean=statistics.mean(v.values()),over177=sum(x>1.77 for x in v.values()),worst=[dict(seed=int(s),judge=v[s],helper=cases[s]['stderr']['helper_end_sec'],req=cases[s]['stderr']['req_sec'],mtime=(R/name/'err'/f'{int(s):04d}.txt').stat().st_mtime)for s in worst],judge=v)
    rows.append(row)
a,b=rows[-2],rows[-1];slow=[s for s,v in a['judge'].items()if v>1.77]
summary=dict(base_slow=len(slow),both_slow=sum(b['judge'][s]>1.77 for s in slow),
    candidate_mean_at_base_slow=statistics.mean(b['judge'][s]for s in slow),
    candidate_mean_else=statistics.mean(v for s,v in b['judge'].items()if s not in slow))
(H/'time-tail.json').write_text(json.dumps(dict(rows=rows,summary=summary),indent=2)+'\n')
for r in rows:print(r['run'],'mean',r['mean'],'over1.77',r['over177'],'worst',r['worst'][:20])
print('summary',summary)
