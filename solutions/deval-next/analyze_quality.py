"""Fresh-list and real-list paired errors; seed is the independent unit."""
from pathlib import Path
import argparse,json
import numpy as np
RUNS=Path('/home/sato/ahc074/runs')
def load(run):
    out={}
    for c in json.loads((RUNS/run/'result.json').read_text())['cases']:
        sc=c.get('order_scores',[c['score']])
        if min(sc)>0:out[int(c['seed'])]=np.array(sc,dtype=float)
    return out
def compare(ref,cand,seeds=None):
    x=load(ref);y=load(cand)
    ids=sorted(set(x)&set(y))
    if seeds is not None:ids=[i for i in ids if seeds[0]<=i<seeds[1]]
    groups={}
    for name,sl in [('all',slice(None)),('real',slice(0,1)),('fresh',slice(1,None))]:
        if name=='fresh' and len(x[ids[0]])==1:continue
        # cmp_variant.py convention: log of the mean moves on the lists.
        b=np.array([x[i][sl].mean() for i in ids]);c=np.array([y[i][sl].mean() for i in ids]);d=100*np.log(c/b)
        groups[name]={'mean':float(d.mean()),'se':float(d.std(ddof=1)/len(ids)**.5),'wtl':[int((d<0).sum()),int((d==0).sum()),int((d>0).sum())],
                      'moves_per_order':float(((c-b)/1024).mean()),'reference_score':float(b.mean()),'candidate_score':float(c.mean())}
    return {'reference':ref,'candidate':cand,'n':len(ids),'seeds':[min(ids),max(ids)+1],'results':groups}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate',nargs='+');p.add_argument('--seeds',default='0-500');p.add_argument('--output',required=True);a=p.parse_args()
    out=[compare(a.reference,c,tuple(map(int,a.seeds.split('-')))) for c in a.candidate]
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
    for r in out:print(r['candidate'],r['n'],' '.join(f"{k}: {v['mean']:+.4f} +- {v['se']:.4f}%" for k,v in r['results'].items()))
