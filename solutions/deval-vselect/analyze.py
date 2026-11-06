"""Replay quality and normal-run stage timing. Run under the shared flock."""
from pathlib import Path
import json,re,sys
import numpy as np
HERE=Path(__file__).resolve().parent
RUNS=Path('/home/sato/ahc074/runs')
def scores(run):
    return {int(c['seed']):np.asarray(c.get('order_scores',[c['score']]),float)
            for c in json.loads((RUNS/run/'result.json').read_text())['cases']}
def compare(base,run,lo=0,hi=1000):
    b=scores(base);v=scores(run);seeds=sorted(s for s in set(b)&set(v) if lo<=s<hi)
    assert all(len(v[s])==8 and len(b[s])==8 and min(v[s])>0 and min(b[s])>0 for s in seeds), 'Incomplete or invalid replay'
    out={'n':len(seeds)}
    for name,sl in [('real',slice(0,1)),('all8',slice(0,8)),('lists1_7',slice(1,8))]:
        z=np.array([100*np.log(v[s][sl].mean()/b[s][sl].mean()) for s in seeds])
        out[name]={'mean':float(z.mean()),'se':float(z.std(ddof=1)/len(z)**.5),
                   'wtl':[int((z<0).sum()),int((z==0).sum()),int((z>0).sum())]}
    return out
def timing(run):
    rows=[];values={}
    cache=RUNS/run/'metrics.json'
    if cache.exists():
        rows=[dict(c['stderr']) for c in json.loads(cache.read_text())['cases'].values()]
    else:
        rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+0-9.eE]+)$',f.read_text(),re.M)}
              for f in (RUNS/run/'err').glob('*.txt')]
    for d in rows:
        if 'end_sec' not in d:continue
        d['judge']=1.04*d['helper_end_sec']+1.35*d['req_sec']+(d['end_sec']-d['helper_end_sec']-d['req_sec'])
        for k,v in d.items():values.setdefault(k,[]).append(v)
    keys=['helper_end_sec','req_sec','end_sec','judge','map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','dv_candidates','dv_chosen','dv_first','dv_best','light_requests']
    return {k:{'mean':float(np.mean(values[k])),'p99':float(np.quantile(values[k],.99)),'max':max(values[k]),
               'gt1.8':int((np.array(values[k])>1.8).sum()),'gt1.9':int((np.array(values[k])>1.9).sum()),'gt2':int((np.array(values[k])>2).sum())}
            for k in keys if k in values}
if __name__=='__main__':
    out=[]
    for row in [json.loads(line) for line in (HERE/'experiments.jsonl').read_text().splitlines()]:
        result=row|{'quality':compare('20261107-015743_deval-seed',row['replay']),'time':timing(row['design'])}
        out.append(result)
        q=result['quality'];t=result['time']
        print(row['tag'],f"n={q['n']}",*[f"{k}: {q[k]['mean']:+.4f} ± {q[k]['se']:.4f}%" for k in ['lists1_7','all8','real']],
              f"design={t['helper_end_sec']['mean']:.3f} judge={t['judge']['mean']:.3f} max={t['judge']['max']:.3f}")
    (HERE/'analysis.json').write_text(json.dumps(out,indent=2))
