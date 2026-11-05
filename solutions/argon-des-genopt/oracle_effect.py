"""Diagnose the model-selected oracle on recorded outputs (no solution execution)."""
import argparse,json,re,statistics,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--output',default='oracle-effect.json');a=p.parse_args()
names=[a.base,a.candidate]
cache=[json.loads((ROOT/n/'metrics.json').read_text())['cases']for n in names]
def queries(name,seed):
    roles=re.search(r'^@paper role = (.*)$',(ROOT/name/'err'/f'{int(seed):04d}.txt').read_text(),re.M)[1].split()
    with (ROOT/name/'out'/f'{int(seed):04d}.txt').open()as f:
        for _ in range(192):f.readline()
        result=[]
        for _ in range(1024):
            count=int(f.readline());ops=[tuple(map(int,f.readline().split()))for _ in range(count)]
            result.append({'ops':ops,'generic':sum(roles[k]=='generic'for k,d in ops)})
    return result
rows=[]
for seed in sorted(cache[0],key=int):
    x,y=(c[seed]for c in cache);m=y['stderr']
    row={'seed':int(seed),'prediction':m['d1_oracle_delta'],'score_delta':y['score']-x['score'],'applied':m['d1_applied']}
    if row['applied']:
        q0,q1=(queries(n,seed)for n in names)
        row['generic_delta']=sum(q['generic']for q in q1)-sum(q['generic']for q in q0)
        row['other_delta']=row['score_delta']-row['generic_delta']
        row['changed_queries']=[{'r':r,'moves_delta':len(b['ops'])-len(a['ops']),
                                'generic_delta':b['generic']-a['generic']}for r,(a,b)in enumerate(zip(q0,q1))if a['ops']!=b['ops']]
    rows.append(row)
def stats(v):return {'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v))}
out={'base':a.base,'candidate':a.candidate,'n':len(rows),'applied':sum(r['applied']for r in rows),
     'prediction':stats([r['prediction']for r in rows]),'actual_moves_per_order':stats([r['score_delta']/1024 for r in rows]),
     'actual_generic_per_order':stats([r.get('generic_delta',0)/1024 for r in rows]),
     'rows':[r for r in rows if r['applied']]}
(HERE/a.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items()if k!='rows'},indent=2))
for row in out['rows']:
    print(row['seed'],row['prediction'],row['score_delta'],row['generic_delta'],len(row['changed_queries']),
          sorted(row['changed_queries'],key=lambda r:abs(r['moves_delta']),reverse=True)[:5])
