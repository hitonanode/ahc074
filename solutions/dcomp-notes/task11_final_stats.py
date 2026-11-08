"""Task11 final 4-way comparison. Run under common flock + nice."""
from pathlib import Path
import argparse,collections,hashlib,json,math,re
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('runs',nargs=4,help='argon, combo-m1-nine, dcomp-combo-alt1, final candidate')
p.add_argument('--output',required=True)
a=p.parse_args();R=Path('/home/sato/ahc074/runs')
rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def stats(x):
    x=np.asarray(x,float)
    return dict(n=len(x),mean=float(x.mean()),se=float(x.std(ddof=1)/math.sqrt(len(x))),
                p99=float(np.percentile(x,99)),max=float(x.max()))
def read(rid):
    d=R/rid;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
    cs=sorted(json.loads((d/'result.json').read_text())['cases'],key=lambda c:int(c['seed']))
    assert [int(c['seed']) for c in cs]==list(range(2000))
    assert all(c['score']>0 for c in cs)
    rows=[]
    for i in range(2000):
        z={k:float(v) for k,v in rx.findall((d/'err'/f'{i:04d}.txt').read_text())}
        z['judge_sec']=z['end_sec']+.04*z['helper_end_sec']+.35*z['req_sec']
        rows.append(z)
    keys=['helper_end_sec','req_sec','end_sec','judge_sec','map_end_sec','dv_anneal_sec',
          'dv_finish_sec','dv_eval_sec','dv_candidates','dv_chosen']
    ts={k:np.array([r[k] for r in rows]) for k in keys if all(k in r for r in rows)}
    return np.array([c['score'] for c in cs]),ts,m
loaded={r:read(r) for r in a.runs}
argon,combo,alt,candidate=a.runs
assert np.all(loaded[alt][1]['dv_candidates']==9)
assert np.all(loaded[candidate][1]['dv_candidates']==loaded[candidate][1]['dv_candidates'][0])
out={'runs':a.runs,'comparisons':{},'timing':{},'paired':{},'p99':{},'source_sha256':{},'outside_load':{}}
for candidate in [alt,a.runs[3]]:
    out['comparisons'][candidate]={}
    for ref in [combo,alt]:
        result={}
        for label,lo,hi in [('all',0,2000),('0-999',0,1000),('1000-1999',1000,2000),
                            ('train',0,500),('500-999',500,1000),('500-1999',500,2000)]:
            x=loaded[ref][0][lo:hi];y=loaded[candidate][0][lo:hi];d=y-x
            result[label]={'pct':stats(100*np.log(y/x)),'moves':stats(d/1024),
                           'wtl':[int(sum(d<0)),int(sum(d==0)),int(sum(d>0))]}
        out['comparisons'][candidate][ref]=result
for rid,(_,ts,m) in loaded.items():
    out['timing'][rid]={k:stats(v) for k,v in ts.items() if k.endswith('_sec')}
    out['timing'][rid]['judge_ratio_argon']=float(ts['judge_sec'].mean()/loaded[argon][1]['judge_sec'].mean())
    out['timing'][rid]['end_above']={str(t):int(sum(ts['end_sec']>t)) for t in [1.8,1.9,2.]}
    if 'dv_chosen' in ts:out['timing'][rid]['chosen']=dict(collections.Counter(map(int,ts['dv_chosen'])))
    out['source_sha256'][rid]=hashlib.sha256((R/rid/'src/main.cpp').read_bytes()).hexdigest()
    out['outside_load'][rid]=m.get('outside_load')
for ref in [combo,alt]:
    b=loaded[ref][1];c=loaded[a.runs[3]][1]
    out['paired'][ref]={k:stats(c[k]-b[k]) for k in ['helper_end_sec','req_sec','end_sec','judge_sec']}
    rng=np.random.default_rng(20261109);values=[]
    for _ in range(40):
        ix=rng.integers(0,2000,(100,2000))
        values.extend(np.percentile(c['judge_sec'][ix],99,axis=1)-np.percentile(b['judge_sec'][ix],99,axis=1))
    out['p99'][ref]={'difference':float(np.percentile(c['judge_sec'],99)-np.percentile(b['judge_sec'],99)),
                     'ci95':list(map(float,np.percentile(values,[2.5,97.5]))),'resamples':4000,'seed':20261109}
# The design must remain exactly the parent's, including the initial paper order.
out['design_identity']={}
for ref in [combo,alt]:
    same=0;different=[]
    for seed in range(2000):
        def papers(rid):
            with (R/rid/'out'/f'{seed:04d}.txt').open('rb') as f:
                return b''.join(f.readline() for _ in range(192))
        if papers(ref)==papers(a.runs[3]):same+=1
        else:different.append(seed)
    out['design_identity'][ref]={'same':same,'total':2000,'different':different}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
for candidate in [alt,a.runs[3]]:
    for ref in [combo,alt]:
        r=out['comparisons'][candidate][ref]['all'];q=r['pct']
        print(candidate,'vs',ref,f"{q['mean']:+.6f} +/- {q['se']:.6f}%",r['wtl'])
for rid in a.runs:
    t=out['timing'][rid]
    print(rid,'judge',t['judge_sec']['mean'],'ratio',t['judge_ratio_argon'],'p99',t['judge_sec']['p99'])
print('paired helper vs alt1:',out['paired'][alt]['helper_end_sec'])
