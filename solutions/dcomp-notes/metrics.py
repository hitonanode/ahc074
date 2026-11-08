"""Paired scores/times, design profiles and tabu diagnostics. Run under flock + nice."""
from pathlib import Path
import argparse, collections, json, math, re
import numpy as np

P=argparse.ArgumentParser()
P.add_argument('reference');P.add_argument('candidates',nargs='+')
P.add_argument('--seeds',default='0-2000');P.add_argument('--output',required=True)
args=P.parse_args();lo,hi=map(int,args.seeds.split('-'))
R=Path('/home/sato/ahc074/runs')
rx=re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',re.M)

def summary(x):
    x=np.asarray(x,dtype=float)
    return dict(n=len(x),mean=float(x.mean()),se=float(x.std(ddof=1)/math.sqrt(len(x))) if len(x)>1 else 0,
                p50=float(np.percentile(x,50)),p99=float(np.percentile(x,99)),max=float(x.max()))
def read(run):
    d=R/run;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok',(run,m['status'])
    cs={int(c['seed']):c for c in json.loads((d/'result.json').read_text())['cases'] if lo<=int(c['seed'])<hi}
    assert cs and all(c['score']>0 for c in cs.values()),run
    rows={};finishes=collections.defaultdict(list)
    for seed in cs:
        t=(d/'err'/f'{seed:04d}.txt').read_text()
        row={k:float(v) for k,v in rx.findall(t)}
        if all(k in row for k in ('helper_end_sec','req_sec','end_sec')):
            row['judge_sec']=1.04*row['helper_end_sec']+1.35*row['req_sec']+row['end_sec']-row['helper_end_sec']-row['req_sec']
        rows[seed]=row
        for cid,extra,key,value in re.findall(r'^@dcomp_finish (\d+) (\d+) ([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$',t,re.M):
            if key.endswith('_sec') or key in ('match_changed','d2_rematch_changed','perforation_trials'):
                finishes[(int(cid),int(extra),key)].append(float(value))
    return cs,rows,m,finishes

b,br,bm,bf=read(args.reference)
out={'reference':args.reference,'range':[lo,hi],'results':{}}
for run in args.candidates:
    c,cr,cm,cf=read(run);seeds=sorted(b.keys()&c.keys())
    r={'n':len(seeds),'score':{},'stage':{},'diagnostics':{},'outside_load':cm.get('outside_load'),
       'finish_profile':{f'{cid}:{extra}:{key}':summary(v) for (cid,extra,key),v in cf.items()}}
    for label,j0,j1 in [('real',0,1),('all',0,8),('fresh',1,8)]:
        moves=[];pct=[]
        for s in seeds:
            x=np.array(b[s].get('order_scores',[b[s]['score']])[j0:j1],dtype=float)
            y=np.array(c[s].get('order_scores',[c[s]['score']])[j0:j1],dtype=float)
            if not len(x) or not len(y):continue
            assert len(x)==len(y) and min(x.min(),y.min())>0
            moves.append((y.mean()-x.mean())/1024);pct.append(100*np.log(y/x).mean())
        if moves:
            r['score'][label]={'moves':summary(moves),'pct':summary(pct),'wtl':[int(sum(v<0 for v in moves)),int(sum(v==0 for v in moves)),int(sum(v>0 for v in moves))]}
    keys=set.intersection(*(set(cr[s]) for s in seeds))
    for k in sorted(keys):
        if k.endswith('_sec') or k.startswith(('dprof_','dc_','af_')) or k in ('map_iters','gobj_before','gobj_after','dv_candidates','anneal_iters'):
            values=[cr[s][k] for s in seeds];z=summary(values)
            if all(k in br[s] for s in seeds):
                reference=[br[s][k] for s in seeds]
                z['reference_mean']=float(np.mean(reference));z['paired_delta']=summary(np.array(values)-reference)
                z['mean_ratio']=float(np.mean(values)/np.mean(reference)) if np.mean(reference) else None
            (r['stage'] if k.endswith('_sec') else r['diagnostics'])[k]=z
    r['chosen']=dict(collections.Counter(str(int(cr[s].get('dv_chosen',-1))) for s in seeds))
    for phase in (0,1):
        key=f'dc_stall_iters_{phase}'
        if key in keys:
            selected=[s for s in seeds if cr[s][key]>0]
            r['diagnostics'][f'stalled_seeds_{phase}']=selected
            r['diagnostics'][f'stalled_cases_{phase}']=len(selected)
    out['results'][run]=r
Path(args.output).write_text(json.dumps(out,indent=2)+'\n')
for name,r in out['results'].items():
    print(name, 'n=',r['n'])
    for label,s in r['score'].items():
        print(label, f"{s['pct']['mean']:+.6f} +/- {s['pct']['se']:.6f}%", f"{s['moves']['mean']:+.6f} +/- {s['moves']['se']:.6f} moves", s['wtl'])
    for k in ('helper_end_sec','req_sec','judge_sec'):
        if k in r['stage']:
            s=r['stage'][k];print(k, 'mean/p99/max',s['mean'],s['p99'],s['max'],'paired',s.get('paired_delta',{}).get('mean'))
    print('stalled cases', [r['diagnostics'].get(f'stalled_cases_{i}') for i in (0,1)])
