#!/usr/bin/env python3
"""Independent exhaustive transition / sampled-goal and matching checks."""
import argparse, ctypes as C, itertools, json, random, sys, time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
from optimize import Design, Engine, Matcher, guard_windows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('design');ap.add_argument('--lib',default='/mnt/data/libjoint.so');ap.add_argument('--out',required=True)
    a=ap.parse_args();started=time.monotonic();d=Design(a.design);e=Engine(d,a.lib);rng=random.Random(732053)
    perms=list(itertools.permutations(range(6)));ix={p:i for i,p in enumerate(perms)}
    rows=[];cols=[]
    for i,p in enumerate(perms):
        for at in range(5):
            for to in range(6):
                if at==to:continue
                q=list(p);k=q.pop(at);q.insert(to,k);rows.append(i);cols.append(ix[tuple(q)])
    mat=csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(720,720))
    expected=shortest_path(mat,directed=True,unweighted=True).astype(np.uint8)
    actual=np.empty((720,720),dtype=np.uint8)
    e.lib.joint_distances(e.handle,actual.ctypes.data_as(C.POINTER(C.c_ubyte)))
    assert np.array_equal(expected,actual)
    guards=guard_windows(d,e);mutable=[j for j in range(36) if j not in guards];initial=e.choice.copy()
    checked=0;valid_goals=0;visibility_states=0;group_checks=0
    for trial in range(12):
        choices=initial.copy()
        for j in rng.sample(mutable,1+trial%5):choices[j]=rng.randrange(120)
        e.layout(choices);graph=e.evaluate();lookup={(int(r[0]),int(r[1])):r for r in graph}
        op=[0]*6;bl=[0]*6
        for j,t in enumerate(choices):
            m,b=map(int,e.rules[t])
            for k in range(6):
                if m>>k&1:op[k]|=1<<j
                if b>>k&1:bl[k]|=1<<j
        codes=[]
        for p in perms:
            cov=0;code=0;visible=[]
            for k in p:
                if op[k]&~cov:visible.append(k)
                code|=bl[k]&~cov;cov|=op[k]
            assert visible==list(p[:5]);codes.append(code);visibility_states+=1
        codes=np.array(codes,dtype=np.uint64)
        cases=[tuple(sorted(rng.sample(range(256),2))) for _ in range(100)]
        cases+=list(lookup)[:40]
        for u,v in cases:
            hs=np.uint64((int(d.A[u])^int(d.A[v]))&((1<<36)-1))
            fu=np.flatnonzero(((codes^d.A[u])&hs)==0);fv=np.flatnonzero(((codes^d.A[v])&hs)==0)
            ok=len(fu)>0 and len(fv)>0
            assert ((u,v) in lookup)==ok
            if ok:
                r=lookup[u,v];cu=int(expected[:,fu].min(axis=1).sum());cv=int(expected[:,fv].min(axis=1).sum())
                assert (cu,cv)==(r[2],r[3]);valid_goals+=2
            checked+=1
        # Group restriction/caching must equal rebuilding the entire altered layout.
        js=rng.sample(mutable,2);neg=(1<<js[1]) if trial%2 else 0;t=rng.randrange(120)
        complement=next(k for k,(m,b) in enumerate(e.rules) if m==e.rules[t,0] and b==(e.rules[t,0]^e.rules[t,1]))
        proposal=choices.copy()
        for j in js:proposal[j]=complement if neg>>j&1 else t
        quick=e.evaluate_group(js,neg,t);e.layout(proposal);slow=e.evaluate()
        assert np.array_equal(quick,slow);group_checks+=1
    # 67 zero-cost forced edges + two odd triangles requiring one expensive bridge.
    padding=[[2*i,2*i+1,0,0,0,0] for i in range(67)]
    tri=[(0,1,1),(1,2,1),(0,2,1),(3,4,1),(4,5,1),(3,5,1),(2,3,10)]
    graph=np.array(padding+[[134+u,134+v,0,0,w,0] for u,v,w in tri],dtype=np.int32)
    matcher=Matcher();r=matcher.solve(graph);assert r and abs(r['objective']-7.8)<1e-8 and matcher.counts['milp']>0
    # Removing the bridge leaves max integer cardinality 69 despite fractional cardinality 70.
    assert matcher.solve(graph[:-1]) is None
    # Independent brute-force tiny matching optima embedded in the same 256-vertex API.
    brute_checks=0
    for trial in range(20):
        small=[(u,v,rng.randrange(1,20)) for u in range(8) for v in range(u+1,8) if rng.random()<.7]
        best=float('inf')
        for es in itertools.combinations(small,3):
            if len({u for edge in es for u in edge[:2]})==6:best=min(best,sum(x[2] for x in es)*.65)
        g=np.array(padding+[[134+u,134+v,0,0,w,0] for u,v,w in small],dtype=np.int32)
        ans=Matcher().solve(g);assert (ans is None)==(not np.isfinite(best))
        if ans is not None:assert abs(ans['objective']-best)<1e-7
        brute_checks+=1
    out=dict(status='passed',all_directed_distances=720*720,visibility_states=visibility_states,
             sampled_pairs=checked,exact_goal_costs=valid_goals,group_rebuild_checks=group_checks,
             odd_cycle_milp=True,infeasible_odd_cycle=True,brute_force_matching_checks=brute_checks,
             seconds=time.monotonic()-started)
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));e.close()
if __name__=='__main__':main()
