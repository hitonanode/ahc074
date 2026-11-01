#!/usr/bin/env python3
"""Exact size-70 pairing for every evaluated display-rule proposal.

The objective is the retained initializer's pair surrogate, not the contest score.
All designs depend on public barcode data only. SciPy/HiGHS proves each retained
matching optimum; missing proofs/timeouts are errors, never silently treated as wins.
"""
from __future__ import annotations
import argparse, ctypes as C, hashlib, json, os, time, warnings
from pathlib import Path
import numpy as np
from scipy.optimize import linprog, milp, Bounds, LinearConstraint, OptimizeWarning
from scipy.sparse import csc_matrix, vstack
warnings.filterwarnings('ignore',category=OptimizeWarning,message='Unrecognized options')

class Design:
    def __init__(self,path):
        ts=Path(path).read_text().split(); assert ts[0]=='JOINT1'; it=iter(ts[1:])
        self.m,self.g,self.h=(int(next(it)) for _ in range(3)); assert (self.m,self.g,self.h)==(6,36,28)
        self.A=np.array([int(next(it)) for _ in range(256)],dtype=np.uint64)
        self.perm=[int(next(it)) for _ in range(64)]; self.handles=[int(next(it)) for _ in range(28)]
        self.paper=np.array([[int(next(it)),int(next(it))] for _ in range(6)],dtype=np.uint64)
        self.edges=[[int(next(it)) for _ in range(3)] for _ in range(36)]
        n=int(next(it)); assert n==186
        self.units=[[int(next(it)) for _ in range(3)] for _ in range(n)]
        self.model=float(next(it)); assert not list(it)
    def write(self,path):
        rows=['JOINT1','6 36 28',' '.join(map(str,self.A)),' '.join(map(str,self.perm)),' '.join(map(str,self.handles))]
        rows+=[' '.join(map(str,r)) for r in self.paper]; rows+=[' '.join(map(str,r)) for r in self.edges]
        rows+=['186']+[' '.join(map(str,r)) for r in self.units]+[repr(self.model)]
        Path(path).write_text('\n'.join(rows)+'\n')

class Engine:
    def __init__(self,design,lib='/mnt/data/libjoint.so'):
        self.lib=C.CDLL(str(lib)); ptru=C.POINTER(C.c_uint64); ptri=C.POINTER(C.c_int)
        self.lib.joint_new.argtypes=[ptru,ptru,ptru];self.lib.joint_new.restype=C.c_void_p
        self.lib.joint_delete.argtypes=[C.c_void_p]
        for nm in ['joint_rules','joint_choices','joint_layout']:
            getattr(self.lib,nm).argtypes=[C.c_void_p,ptri]
        self.lib.joint_evaluate.argtypes=[C.c_void_p,C.c_int,C.c_int,ptri];self.lib.joint_evaluate.restype=C.c_int
        self.lib.joint_evaluate_group.argtypes=[C.c_void_p,C.c_uint64,C.c_uint64,C.c_int,ptri];self.lib.joint_evaluate_group.restype=C.c_int
        self.lib.joint_distances.argtypes=[C.c_void_p,C.POINTER(C.c_ubyte)]
        a=np.ascontiguousarray(design.A);o=np.ascontiguousarray(design.paper[:,0]);b=np.ascontiguousarray(design.paper[:,1])
        self.handle=self.lib.joint_new(*(x.ctypes.data_as(ptru) for x in [a,o,b]));assert self.handle
        self.rules=np.empty((120,2),dtype=np.int32);self.lib.joint_rules(self.handle,self.rules.ctypes.data_as(ptri))
        self.choice=np.empty(36,dtype=np.int32);self.lib.joint_choices(self.handle,self.choice.ctypes.data_as(ptri))
        self.buffer=np.empty((32640,6),dtype=np.int32)
        self.two=np.array([int(x).bit_count()==2 for x in self.rules[:,0]])
    def layout(self,choice):
        self.choice=np.ascontiguousarray(choice,dtype=np.int32)
        self.lib.joint_layout(self.handle,self.choice.ctypes.data_as(C.POINTER(C.c_int)))
    def evaluate(self,j=-1,t=0):
        n=self.lib.joint_evaluate(self.handle,j,t,self.buffer.ctypes.data_as(C.POINTER(C.c_int)))
        return self.buffer[:n].copy()
    def evaluate_group(self,group,negative,t):
        erased=sum(1<<j for j in group)
        n=self.lib.joint_evaluate_group(self.handle,erased,negative,t,self.buffer.ctypes.data_as(C.POINTER(C.c_int)))
        return self.buffer[:n].copy()
    def close(self):
        if self.handle:self.lib.joint_delete(self.handle);self.handle=None

def weights(graph,handle_weight=0.65):
    return graph[:,4]*handle_weight+graph[:,5]*.04+(graph[:,2]+graph[:,3])/720.0

class Matcher:
    def __init__(self,handle_weight=.65):
        self.counts=dict(trivial_bound=0,lp=0,milp=0,integral_lp=0,lp_bound=0,infeasible=0)
        self.handle_weight=handle_weight
    def solve(self,graph,cutoff=float('inf')):
        if len(graph)<70:self.counts['infeasible']+=1;return None
        c=weights(graph,self.handle_weight);lo=float(np.partition(c,69)[:70].sum())
        if lo>=cutoff-1e-8:self.counts['trivial_bound']+=1;return None
        n=len(c);idx=np.arange(n,dtype=np.int32)
        mat=csc_matrix((np.ones(2*n),(graph[:,:2].T.reshape(-1),np.tile(idx,2))),shape=(256,n))
        card=csc_matrix(np.ones((1,n)))
        self.counts['lp']+=1
        r=linprog(c,A_ub=mat,b_ub=np.ones(256),A_eq=card,b_eq=[70],bounds=(0,1),method='highs',options={'threads':1})
        if r.status==2:self.counts['infeasible']+=1;return None
        if not r.success:raise RuntimeError(r.message)
        if r.fun>=cutoff-1e-8:self.counts['lp_bound']+=1;return None
        if np.max(np.abs(r.x-np.rint(r.x)))<1e-6:self.counts['integral_lp']+=1
        else:
            self.counts['milp']+=1
            constraint=LinearConstraint(vstack([mat,card],format='csc'),np.r_[np.full(256,-np.inf),70],np.r_[np.ones(256),70])
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                r=milp(c,integrality=np.ones(n),bounds=Bounds(0,1),constraints=constraint,
                       options={'mip_rel_gap':0.0,'time_limit':30.0,'threads':1})
            if r.status==2:self.counts['infeasible']+=1;return None
            if not r.success or r.mip_gap>1e-8:raise RuntimeError(f'Unproven matching: {r}')
        chosen=np.flatnonzero(r.x>.5)
        assert len(chosen)==70 and len(set(map(int,graph[chosen,:2].ravel())))==140
        val=float(c[chosen].sum());assert abs(val-r.fun)<1e-5
        if val>=cutoff-1e-8:return None
        return {'objective':val,'pairs':graph[chosen,:2].tolist(),
                'generic_sum':float((graph[chosen,2]+graph[chosen,3]).sum()/720),
                'handle_diff_sum':int(graph[chosen,4].sum()),'full_diff_sum':int(graph[chosen,5].sum()),
                'compatible_edges':len(graph),'optimal':True}

def guard_windows(d,engine):
    freq=np.zeros(36,dtype=int)
    for a,b,_ in d.units:
        if b>=0:
            diff=int(d.A[a])^int(d.A[b]);freq+=[diff>>j&1 for j in range(36)]
    byedge={}
    for j,t in enumerate(engine.choice):byedge.setdefault(int(engine.rules[t,0]),[]).append(j)
    assert len(byedge)==15
    return [min(js,key=lambda j:(freq[j],j)) for js in byedge.values()]

def save_candidate(d,engine,choice,result,prefix):
    prefix=Path(prefix);prefix.parent.mkdir(parents=True,exist_ok=True)
    # The old unit list may become unrealizable under the candidate layout. Replace
    # it by a harmless valid placeholder assignment for reading before refitting.
    # Actual columns are supplied by the retained Design initializer in stage=refit.
    paper=np.zeros((6,2),dtype=np.uint64)
    for j,t in enumerate(choice):
        m,b=map(int,engine.rules[t])
        for k in range(6):
            if m>>k&1:paper[k,0]|=np.uint64(1)<<np.uint64(j)
            if b>>k&1:paper[k,1]|=np.uint64(1)<<np.uint64(j)
    oldpaper=d.paper.copy();oldunits=d.units
    d.paper=paper
    pairunits=[];used=set()
    for a,b in result['pairs']:
        cols=[c for c,j in enumerate(d.handles) if ((int(d.A[a])^int(d.A[b]))>>j&1)==0]
        assert cols
        pairunits.append([a,b,cols[0]]);used|={a,b}
    d.units=pairunits+[[a,-1,0] for a in range(256) if a not in used]
    d.write(str(prefix)+'.design');d.paper=oldpaper;d.units=oldunits
    Path(str(prefix)+'.match').write_text(''.join(f'{a} {b}\n' for a,b in result['pairs']))
    result=dict(result,choices=list(map(int,choice)),nonlinear_windows=int(sum(not engine.two[t] for t in choice)))
    Path(str(prefix)+'.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

def groups_for(d,e,guards,kind):
    groups=[([j],0) for j in range(36) if j not in guards]
    if kind=='single':return groups
    # Whole repeated-edge blocks are changed coherently, respecting their original
    # polarity. Guards remain unchanged. This can cross a two-window barrier.
    byedge={}
    for j,(a,b,p) in enumerate(d.edges):
        if j not in guards:
            if a>b:a,b,p=b,a,p^1
            byedge.setdefault((a,b),[]).append((j,p))
    for members in byedge.values():
        if len(members)<2:continue
        js=[j for j,p in members];pol=members[0][1]
        neg=sum(1<<j for j,p in members if p!=pol)
        groups.append((js,neg))
    return groups

def sweep(d,e,matcher,choice,guards,family,incumbent,log,force_four=False,kind='block'):
    e.layout(choice);best=dict(incumbent);bestchoice=choice.copy();bestmove=None
    if force_four:best={'objective':float('inf')}
    allowed=np.arange(120) if family=='all' else np.flatnonzero(e.two)
    complement=[next(u for u in range(120) if e.rules[u,0]==m and e.rules[u,1]==(m^b)) for m,b in e.rules]
    start=time.monotonic();n=0
    for gi,(js,negative) in enumerate(groups_for(d,e,guards,kind)):
        for t in allowed:
            newchoice=choice.copy()
            for j in js:newchoice[j]=complement[t] if negative>>j&1 else t
            if np.array_equal(newchoice,choice) or (force_four and e.two[t]):continue
            graph=e.evaluate_group(js,negative,int(t));n+=1
            candidate=matcher.solve(graph,best['objective'])
            if candidate is not None:
                best=candidate;bestchoice=newchoice;bestmove=[js,int(t),negative]
                log.append(dict(kind='record',family=family,move=bestmove,objective=best['objective'],
                                nonlinear=not bool(e.two[t]),evaluated=n,elapsed=time.monotonic()-start))
        print(json.dumps(dict(group=js,family=family,evaluated=n,best=best['objective'],elapsed=round(time.monotonic()-start,3))),flush=True)
    log.append(dict(kind='sweep',family=family,evaluated=n,seconds=time.monotonic()-start,move=bestmove,objective=best['objective']))
    return bestchoice,best,bestmove

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('design');ap.add_argument('--out',required=True)
    ap.add_argument('--lib',default='/mnt/data/libjoint.so');ap.add_argument('--sweeps',type=int,default=1)
    ap.add_argument('--kind',choices=['single','block'],default='block');ap.add_argument('--force-four',action='store_true')
    ap.add_argument('--family',choices=['two','all','both'],default='both');ap.add_argument('--handle-weight',type=float,default=.65)
    args=ap.parse_args();start=time.monotonic();d=Design(args.design);e=Engine(d,args.lib);matcher=Matcher(args.handle_weight)
    initial=e.choice.copy();guards=guard_windows(d,e);graph=e.evaluate();exact=matcher.solve(graph);assert exact
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True);log=[]
    lookup={(int(x[0]),int(x[1])):float(w) for x,w in zip(graph,weights(graph,args.handle_weight))}
    original_cost=sum(lookup[tuple(sorted((a,b)))] for a,b,_ in d.units if b>=0)
    save_candidate(d,e,initial,exact,out/'pair-only')
    print('BASE',original_cost,exact,flush=True)
    final={}
    for family in ['two','all'] if args.family=='both' else [args.family]:
        choice=initial.copy();best=exact
        for step in range(args.sweeps):
            choice,best,mv=sweep(d,e,matcher,choice,guards,family,best,log,force_four=args.force_four and step==0,kind=args.kind)
            save_candidate(d,e,choice,best,out/f'{family}-{step+1}')
            if mv is None:break
        final[family]=dict(best,choices=choice.tolist(),nonlinear_windows=int(sum(not e.two[t] for t in choice)))
    result=dict(design_sha256=hashlib.sha256(Path(args.design).read_bytes()).hexdigest(),
                original_pair_objective=original_cost,pair_only=exact,final=final,guards=guards,
                controls=vars(args),search_log=log,counts=matcher.counts,seconds=time.monotonic()-start)
    (out/'search.json').write_text(json.dumps(result,indent=2)+'\n');e.close()
if __name__=='__main__':main()
