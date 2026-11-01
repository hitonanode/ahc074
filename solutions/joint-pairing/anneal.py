#!/usr/bin/env python3
"""Non-monotone joint layout/matching exploration, using exact conditional matching.

A sampled Metropolis threshold allows the LP lower bound to reject proposals safely.
This does not round an LP solution. Every accepted state's matching is integral and
optimal to HiGHS tolerance. All choices use public barcodes only.
"""
import argparse,json,math,random,time
from pathlib import Path
import numpy as np
from optimize import Design,Engine,Matcher,guard_windows,groups_for,save_candidate

def explore(d,e,family,steps,seed,out):
    start=time.monotonic();rng=random.Random(seed);m=Matcher();initial=e.choice.copy();guards=guard_windows(d,e)
    groups=groups_for(d,e,guards,'block');allowed=list(range(120)) if family=='all' else list(map(int,np.flatnonzero(e.two)))
    complement=[next(u for u in range(120) if e.rules[u,0]==mask and e.rules[u,1]==(mask^b)) for mask,b in e.rules]
    cur=m.solve(e.evaluate());assert cur
    best=cur;choice=initial.copy();bestchoice=choice.copy();best_four=None;best_four_choice=None
    accepted=0;four_accepted=0;max_four=0;history=[]
    for it in range(steps):
        temp=5.0*(.05/5.0)**(it/max(steps-1,1))
        js,negative=groups[rng.randrange(len(groups))];t=allowed[rng.randrange(len(allowed))]
        candidate=choice.copy()
        for j in js:candidate[j]=complement[t] if negative>>j&1 else t
        threshold=cur['objective']-temp*math.log(max(rng.random(),1e-300))
        if not np.array_equal(candidate,choice):
            graph=e.evaluate_group(js,negative,t);r=m.solve(graph,threshold)
            if r is not None:
                cur=r;choice=candidate;e.layout(choice);accepted+=1
                nf=sum(not e.two[t] for t in choice);max_four=max(max_four,nf)
                if nf:
                    four_accepted+=1
                    if best_four is None or cur['objective']<best_four['objective']:
                        best_four=cur;best_four_choice=choice.copy()
                if cur['objective']<best['objective']-1e-8:best=cur;bestchoice=choice.copy()
        if (it+1)%100==0 or it+1==steps:
            history.append(dict(iteration=it+1,current=cur['objective'],best=best['objective'],accepted=accepted,
                                nonlinear_windows=int(sum(not e.two[t] for t in choice)),temperature=temp,seconds=time.monotonic()-start))
            print(json.dumps(dict(family=family,**history[-1])),flush=True)
    save_candidate(d,e,bestchoice,best,out/f'deep-{family}')
    if best_four is not None:save_candidate(d,e,best_four_choice,best_four,out/'deep-forced-four')
    return dict(family=family,best=best,best_choices=bestchoice.tolist(),best_nonlinear_windows=int(sum(not e.two[t] for t in bestchoice)),
                best_four=best_four,accepted=accepted,four_accepted=four_accepted,max_four=max_four,
                history=history,counts=m.counts,seconds=time.monotonic()-start,steps=steps,seed=seed)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('design');ap.add_argument('--out',required=True);ap.add_argument('--lib',default='/mnt/data/libjoint.so')
    ap.add_argument('--steps',type=int,default=3000);ap.add_argument('--seed',type=int,default=3911707)
    a=ap.parse_args();d=Design(a.design);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);results={}
    for family in ['two','all']:
        e=Engine(d,a.lib);results[family]=explore(d,e,family,a.steps,a.seed,out);e.close()
    (out/'deep.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
