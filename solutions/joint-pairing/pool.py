#!/usr/bin/env python3
"""Enumerate guarded one-window and repeated-edge-block neighborhoods.

Keep 8 linear and 4 nonlinear alternatives by exact conditional size-70 matching.
The nonlinear pool is kept even when its surrogate is worse: column refitting and
independent simulated orders will test whether that surrogate rejected good designs.
"""
import argparse, json, time
from pathlib import Path
import numpy as np
from optimize import Design, Engine, Matcher, guard_windows, groups_for, save_candidate, weights


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('design');ap.add_argument('--out',required=True)
    ap.add_argument('--lib',default='/mnt/data/libjoint.so');ap.add_argument('--linear',type=int,default=8);ap.add_argument('--nonlinear',type=int,default=4)
    a=ap.parse_args();t0=time.monotonic();d=Design(a.design);e=Engine(d,a.lib);m=Matcher();original=e.choice.copy();guards=guard_windows(d,e)
    graph=e.evaluate();base=m.solve(graph);assert base
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);save_candidate(d,e,original,base,out/'pair-only')
    lookup={(int(x[0]),int(x[1])):float(w) for x,w in zip(graph,weights(graph))}
    original_cost=sum(lookup[tuple(sorted((u,v)))] for u,v,_ in d.units if v>=0)
    pools={'linear':[],'nonlinear':[]};cap={'linear':a.linear,'nonlinear':a.nonlinear}
    complement=[next(u for u in range(120) if e.rules[u,0]==mask and e.rules[u,1]==(mask^b)) for mask,b in e.rules]
    inspected=0;seen=set();trace=[]
    for js,negative in groups_for(d,e,guards,'block'):
        for r in range(120):
            choice=original.copy()
            for j in js:choice[j]=complement[r] if negative>>j&1 else r
            key=tuple(map(int,choice))
            if key==tuple(original) or key in seen:continue
            seen.add(key);inspected+=1
            fam='linear' if e.two[r] else 'nonlinear';pool=pools[fam]
            bound=pool[-1]['objective'] if len(pool)==cap[fam] else float('inf')
            graph=e.evaluate_group(js,negative,r);result=m.solve(graph,bound)
            if result is None:continue
            result.update(choices=choice.tolist(),move=dict(windows=js,negative=negative,rule=r))
            oldpairs=set(tuple(sorted(p)) for p in base['pairs']);newpairs=set(tuple(sorted(p)) for p in result['pairs'])
            valid=set(map(tuple,graph[:,:2].tolist()))
            result['broken_old_pairs']=len(oldpairs-valid);result['replaced_pairs']=len(oldpairs-newpairs)
            pool.append(result);pool.sort(key=lambda x:(x['objective'],x['choices']));del pool[cap[fam]:]
        trace.append(dict(group=js,proposals=inspected,best={k:v[0]['objective'] if v else None for k,v in pools.items()},seconds=time.monotonic()-t0))
        print(json.dumps(trace[-1]),flush=True)
    for fam,pool in pools.items():
        for i,r in enumerate(pool):save_candidate(d,e,np.array(r['choices']),r,out/f'{fam}-{i}')
    summary=dict(original_pair_objective=original_cost,pair_only=base,pools=pools,guards=guards,
                 counts=m.counts,proposals=inspected,seconds=time.monotonic()-t0,trace=trace,controls=vars(a))
    (out/'pool.json').write_text(json.dumps(summary,indent=2)+'\n');e.close()
if __name__=='__main__':main()
