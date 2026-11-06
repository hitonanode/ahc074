"""Final paired normal comparison and seed-disjoint replay evidence.

Run under runs/.lock. Never fit or select a parameter here.
"""
from pathlib import Path
import argparse,json,re,hashlib
import numpy as np
from analyze import RUNS,scores,compare,timing

def normal(reference,candidate):
    a=scores(reference);b=scores(candidate)
    seeds=sorted(set(a)&set(b))
    valid=[s for s in seeds if min(a[s])>0 and min(b[s])>0]
    x=np.array([a[s][0] for s in valid]);y=np.array([b[s][0] for s in valid])
    d=100*np.log(y/x)
    errors={k:sum(c['E'] for c in json.loads((RUNS/r/'metrics.json').read_text())['cases'].values())
            for k,r in [('reference',reference),('candidate',candidate)]}
    return dict(n=len(valid),invalid=len(seeds)-len(valid),display_errors=errors,base_mean=float(x.mean()),candidate_mean=float(y.mean()),
        difference=float(d.mean()),se=float(d.std(ddof=1)/len(d)**.5),
        wtl=[int((y<x).sum()),int((y==x).sum()),int((y>x).sum())])

def guard(run):
    rows=[]
    for f in (RUNS/run/'err').glob('*.txt'):
        d={k:float(v) for k,v in re.findall(r'^(\w+) = ([-+0-9.eE]+)$',f.read_text(),re.M)}
        if 'end_sec' in d:rows.append(d)
    end=np.array([d['end_sec'] for d in rows]);light=np.array([d.get('light_requests',0) for d in rows])
    hard=np.array([d.get('hard_light_requests',0) for d in rows])
    result=json.loads((RUNS/run/'result.json').read_text())
    errors=sum(c['E'] for c in json.loads((RUNS/run/'metrics.json').read_text())['cases'].values())
    return dict(n=len(rows),mean=float(end.mean()),p99=float(np.quantile(end,.99)),max=float(end.max()),
        gt195=int((end>1.95).sum()),gt2=int((end>2).sum()),light_cases=int((light>0).sum()),
        hard_cases=int((hard>0).sum()),light_orders=float(light.mean()),hard_orders=float(hard.mean()),
        wa=sum(c['score']<=0 for c in result['cases']),display_errors=errors)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--reference',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--replay',required=True);p.add_argument('--solution',required=True)
    p.add_argument('--guard',action='append',default=[])
    args=p.parse_args()
    baseline='20261107-015743_deval-seed'
    out=dict(reference=args.reference,candidate=args.candidate,replay=args.replay,replay_reference=baseline)
    out['normal']=normal(args.reference,args.candidate)
    out['time']={key:timing(run) for key,run in [('reference',args.reference),('candidate',args.candidate)]}
    out['judge_ratio']=out['time']['candidate']['judge']['mean']/out['time']['reference']['judge']['mean']
    out['replay_metrics']={key:compare(baseline,args.replay,lo,hi) for key,lo,hi in
        [('all_0_999',0,1000),('train_0_499',0,500),('test_500_999',500,1000)]}
    out['guard']={r:guard(r) for r in args.guard}
    path=Path(args.solution);source=(path/'main.cpp').read_bytes()
    out['source_bytes']=len(source);out['source_sha256']=hashlib.sha256(source).hexdigest()
    out['source_limit_pass']=len(source)<=520000
    (path/'final_metrics.json').write_text(json.dumps(out,indent=2))
    print('normal',out['normal'])
    print('judge ratio',out['judge_ratio'],'base',out['time']['reference']['judge'],'candidate',out['time']['candidate']['judge'])
    for k,v in out['replay_metrics'].items():print(k,v)
    print('guards',out['guard'],'bytes',len(source))
if __name__=='__main__':main()
