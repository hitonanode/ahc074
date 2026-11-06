"""Design-only features. No solver, request stream, or measured label is read.

Numba is used to make research extraction practical; kernels have simple fixed
size loops suitable for C++. Run this script under the shared evaluation flock.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ.setdefault(key,'1')
import sys
sys.dont_write_bytecode=True
import argparse
from pathlib import Path
import json
import itertools
import concurrent.futures
import re
import numpy as np
from numba import njit

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'

@njit(cache=True)
def pc(x):
    n=0
    while x:
        x &= x-np.uint64(1)
        n+=1
    return n

@njit(cache=True)
def highbit(x):
    n=0
    while x:
        x >>= np.uint64(1)
        n+=1
    return n

@njit(cache=True)
def handle_bits(arr,handle):
    out=np.zeros(len(arr),np.uint64)
    for k in range(len(arr)):
        for c in range(len(handle)):
            out[k] |= ((arr[k]>>np.uint64(handle[c])) & np.uint64(1))<<np.uint64(c)
    return out

def poset_table():
    """Uniform-source exact generic-layer costs, copied data from the base solver.

    Its bottom generic sheet cannot move; these are legal distances, not ordinary
    unrestricted permutation edit distances. Kept separate from all training data.
    """
    path=HERE/'posets.npz'
    if path.exists():
        a=np.load(path); return a['keys'],a['means']
    source=(HERE.parent/'argon-des-perf-latew105/main.cpp').read_text()
    body=source.split('constexpr PosetClass kPosetClasses[318] = {',1)[1].split('};',1)[0]
    classes=[(int(k,16),int(v)) for k,v in re.findall(r'\{0x([0-9a-f]+)ULL, (\d+)\}',body)]
    perms=np.array(list(itertools.permutations(range(6))),dtype=np.uint64)
    table={}
    for relation,total in classes:
        rel=np.zeros(720,np.uint64)
        for a in range(6):
            for b in range(6):
                if relation>>(8*a+b)&1:
                    rel |= np.uint64(1) << (8*perms[:,a]+perms[:,b])
        for r in np.unique(rel): table[int(r)]=total/720.
    keys=np.array(sorted(table),np.uint64)
    means=np.array([table[int(k)] for k in keys])
    assert len(keys)==130023
    np.savez(path,keys=keys,means=means)
    return keys,means

@njit(cache=True)
def relations(A,opaque,ded,edge,polarity,G):
    rel=np.zeros(256,np.uint64)
    nrel=np.zeros(256)
    for t in range(256):
        reach=np.zeros(6,np.uint64)
        holes=(~opaque[ded[t]]) & ((np.uint64(1)<<np.uint64(G))-np.uint64(1))
        for j in range(G):
            if not ((holes>>np.uint64(j))&np.uint64(1)): continue
            a,b=edge[j]
            if int((A[t]>>np.uint64(j))&np.uint64(1))!=polarity[j]: a,b=b,a
            reach[a] |= np.uint64(1)<<np.uint64(b)
        for k in range(6):
            for a in range(6):
                if (reach[a]>>np.uint64(k))&np.uint64(1): reach[a]|=reach[k]
        for a in range(6):
            assert not ((reach[a]>>np.uint64(a))&np.uint64(1))
            rel[t] |= reach[a]<<np.uint64(8*a)
            nrel[t]+=pc(reach[a])
    return rel,nrel

def arrays(st):
    A=np.array(st['A'],np.uint64)
    paper=np.array(st['papers'],np.uint64).reshape(-1,2)
    handle=np.array(st['handle'],np.int64)
    col=np.array(st['columns'],np.int64)
    ded=np.array(st['ded'],np.int64)
    hb=handle_bits(A,handle)
    op=handle_bits(paper[:,0],handle)
    bl=handle_bits(paper[:,1],handle)
    return A,paper,handle,col,ded,hb,op,bl

@njit(cache=True)
def counts_kernel(hb,op,bl,col,ded,H):
    nc=np.zeros(H);nt=np.zeros(H);n1=np.zeros(H);p1=np.zeros(H)
    xy=np.zeros((H,2));freq=np.zeros(192)
    for t in range(256):
        k=ded[t];freq[k]+=1;nt[col[k]]+=1
        for c in range(H):
            if not ((op[k]>>np.uint64(c))&np.uint64(1)):
                xy[c,int((hb[t]>>np.uint64(c))&np.uint64(1))]+=1
    for k in range(192):
        c=col[k]
        if c<0: continue
        nc[c]+=1
        b=int((bl[k]>>np.uint64(c))&np.uint64(1))
        n1[c]+=b
        if freq[k]==2:p1[c]+=b
    return nc,nt,n1,p1,xy,freq

def static_features(st,table):
    A,paper,handle,col,ded,hb,op,bl=arrays(st)
    H=st['H']; G=st['G']
    nc,nt,n1,p1,xy,freq=counts_kernel(hb,op,bl,col,ded,H)
    x,y=xy.T
    npa=nt-nc
    costcol=(nc*(nc-1)+npa*(npa-1))/2+np.maximum(0,npa-1)*((p1==0)|(p1==npa))
    rel,nrel=relations(A,paper[:,0],ded,np.array(st['edge']).reshape(-1,2),np.array(st['polarity']),G)
    keys,vals=table
    idx=np.searchsorted(keys,rel)
    assert np.array_equal(keys[idx],rel)
    gc=vals[idx]
    # h: H columns, t: 256 equally likely targets; all arrays are design-derived.
    columns=np.arange(H)
    depth=columns/max(H-1,1)
    minority=np.minimum(x,y)
    demand=x+y
    h={
        'col':costcol/256,'dem':demand/256,'minor':minority/256,
        'balance':np.divide(minority,demand,out=np.zeros(H),where=demand>0),
        'nc':nc,'nt':nt,'np':npa,'unit_minor':np.minimum(n1,nc-n1),
        'pair_minor':np.minimum(p1,npa-p1),'depth':depth,
    }
    for strength in (0,0.5,1,2,4,8):
        r=strength*nt
        p=(y+r*(y>x))/np.maximum(1,demand+r)
        h[f'h{strength:g}']=(x*p+y*(1-p))/256
        h[f'head{strength:g}']=p
    # Per-target columns use majority-invariant colour statistics, avoiding arbitrary polarity.
    t={'col_depth':depth[col[ded]],'pair':freq[ded]-1,'nc':nc[col[ded]],
       'np':npa[col[ded]],'generic':gc,'gen_relations':nrel,
       'gen_holes':np.array([pc((~paper[k,0])&((np.uint64(1)<<np.uint64(G))-np.uint64(1))) for k in ded]),
       'colcost':costcol[col[ded]]/nt[col[ded]]}
    hole=np.array([[(int(op[k])>>c&1)==0 for c in range(H)] for k in ded],dtype=float)
    target=np.array([[int(z)>>c&1 for c in range(H)] for z in hb])
    t['holes']=hole.sum(axis=1)
    t['early_holes']=(hole*(columns[None,:]<col[ded,None])).sum(axis=1)
    t['minor_requests']=(hole*(target!=(y>x)[None,:])).sum(axis=1)
    t['last_hole']=hole[:,-1]
    t['last_minor']=hole[:,-1]*(target[:,-1]!=(y[-1]>x[-1]))
    for strength in (0,0.5,1,2,4,8):
        p=h[f'head{strength:g}']
        wrong=np.where(target,1-p,p)*hole
        t[f'mismatch{strength:g}']=wrong.sum(axis=1)
        t[f'mismatch_var{strength:g}']=(wrong*(1-wrong)).sum(axis=1)
        for band in range(5):
            mask=(columns>=H-5+band)
            t[f'tail{band}_{strength:g}']=(wrong*mask).sum(axis=1)
    t['hole_dem']=(hole*demand/256).sum(axis=1)
    t['hole_min']=(hole*minority/256).sum(axis=1)
    t['hole_bal']=(hole*h['balance']).sum(axis=1)
    t['hole_bal2']=(hole*h['balance']**2).sum(axis=1)
    t['colminor']=np.minimum(n1,nc-n1)[col[ded]]
    # Aggregate columns after nonlinear transforms. No centering across candidate designs here.
    out={'col':costcol.sum()/256,'gc':gc.mean(),'G':float(G),'H':float(H)}
    out['holes']=hole.mean(axis=0).sum()
    out['extra_holes']=t['early_holes'].mean()
    for strength in (0,0.5,1,2,4,8):
        hcost=h[f'h{strength:g}']
        for power in (0,1,2,3):out[f'h{strength:g}_d{power}']=float(np.sum(hcost*depth**power))
        for band in (1,2,3,5):out[f'h{strength:g}_last{band}']=float(hcost[-band:].sum())
        out[f'h{strength:g}_balance']=float(np.sum(hcost*h['balance']))
        out[f'h{strength:g}_balance2']=float(np.sum(hcost*h['balance']**2))
    for name in ('dem','minor','balance','unit_minor','pair_minor','nc','np'):
        for power in (1,2,3):out[f'{name}_p{power}']=float(np.sum(h[name]**power))
    for name in ('generic','gen_holes','gen_relations','holes','early_holes','minor_requests','hole_bal','hole_bal2'):
        for power in (1,2,3):out[f't_{name}_p{power}']=float(np.mean(t[name]**power))
    reconstructed=out['col']+0.76*out['h2_d0']+out['gc']
    if 'baselines' in st:
        assert abs(reconstructed-st['baselines'][4])<1.e-4,(reconstructed,st['baselines'][4])
    return out,t,(hb,op,bl,col,ded,H,nc,nt,n1,p1,xy,freq)

@njit(cache=True)
def donor_tables(hb,op,bl,col,ded,H,prob,freq):
    """Each donor's largest legal interval and its independent-head saving.

    This is a static set-cover surrogate, not a request planner. No paper stack,
    insertion, legal move sequence, real request order, or Solver is constructed.
    """
    covers=np.zeros((256,192),np.uint64)
    starts=np.zeros((256,192),np.int64)
    utility=np.zeros(192)
    for t in range(256):
        own=ded[t]
        for k in range(192):
            c=col[k]
            if c<0 or c==col[own]:continue
            shown=op[k]&~op[own]
            wrong=shown&(bl[k]^hb[t])
            lo=highbit(wrong)
            if lo>c:continue
            cover=shown & ~((np.uint64(1)<<np.uint64(lo))-np.uint64(1))
            covers[t,k]=cover; starts[t,k]=lo
            # Own handle is not a saving if this is already the top paper.
            cv=cover & ~(np.uint64(1)<<np.uint64(c))
            p0=1.;p1_=0.;e=0.
            for j in range(c):
                if not ((cv>>np.uint64(j))&np.uint64(1)):continue
                p=prob[j] if not ((hb[t]>>np.uint64(j))&np.uint64(1)) else 1-prob[j]
                p1_=p1_*(1-p)+p0*p;p0*=1-p;e+=p
            utility[k]+=max(0.,e-(1-p0)-0.6*(1-p0-p1_))
    heads=np.full((H,2),-1,np.int64)
    for k in range(192):
        c=col[k]
        if c<0:continue
        b=int((bl[k]>>np.uint64(c))&np.uint64(1))
        old=heads[c,b]
        if old<0 or freq[k]>freq[old] or (freq[k]==freq[old] and utility[k]>utility[old]):
            heads[c,b]=k
    return covers,starts,utility,heads

def qmc_samples(H,nsamples=128):
    # Scrambled Sobol uniforms: a fixed digital net, no live RNG / order list.
    from scipy.stats import qmc
    return qmc.Sobol(d=H,scramble=True,seed=19790427).random_base2(int(np.log2(nsamples)))

@njit(cache=True)
def cover_expectation(hb,op,bl,col,ded,H,prob,covers,starts,heads,samples,price,stay=np.empty((0,0))):
    """Average interval-cover cost over independent stationary head colours.

    For each target and digital-net point: cover mismatching demanded handles
    with at most two representative donors per column; donors cost `price` plus
    one when their colour differs from the column head. DP allows shortened
    intervals and records only counts/colour transitions. It emits no moves.
    """
    T=np.zeros((256,8))
    flips=np.zeros((H,2))
    ns=len(samples)
    allbits=(np.uint64(1)<<np.uint64(H))-np.uint64(1)
    for s in range(ns):
        colors=np.uint64(0)
        for c in range(H):
            if samples[s,c]<prob[c]: colors|=np.uint64(1)<<np.uint64(c)
        for t in range(256):
            own=ded[t]
            holes=allbits & ~op[own]
            wrong=(colors^hb[t])&holes
            raw=pc(wrong)
            dp=np.zeros(H+1)
            prev=np.full(H+1,-1,np.int64)
            picked=np.full(H+1,-1,np.int64)
            pickdepth=np.zeros(H+1)
            for c in range(H):
                dp[c+1]=dp[c]
                if c==col[own]: continue
                for b in range(2):
                    k=heads[c,b]
                    if k<0: continue
                    cov=covers[t,k]
                    if not cov:continue
                    depth=1. if b!=int((colors>>np.uint64(c))&np.uint64(1)) else 0.
                    saving=pc(cov&wrong)
                    lo=starts[t,k]
                    for start in range(lo,c+1):
                        charge=price-(0.6*stay[k,start] if stay.size else 0.)
                        gain=saving-charge-depth
                        if gain>0 and dp[start]+gain>dp[c+1]+1.e-12:
                            dp[c+1]=dp[start]+gain
                            prev[c+1]=start;picked[c+1]=k;pickdepth[c+1]=depth
                        if (cov & wrong)>>np.uint64(start)&np.uint64(1): saving-=1
                        if saving<=price+depth-(0.6 if stay.size else 0.):break
            covered=np.uint64(0); nf=0.; digs=0.; lifespan=0.
            j=H
            while j>0:
                k=picked[j]
                if k<0:j-=1;continue
                lo=prev[j]
                covered |= covers[t,k]&~((np.uint64(1)<<np.uint64(lo))-np.uint64(1))
                nf+=1;digs+=pickdepth[j]
                lifespan+=j-lo
                j=lo
            left=wrong&~covered
            fixes=pc(left)
            T[t,0]+=raw;T[t,1]+=raw-dp[H];T[t,2]+=fixes
            T[t,3]+=nf;T[t,4]+=digs;T[t,5]+=pc(covered)
            T[t,6]+=lifespan;T[t,7]+=fixes*fixes
            for c in range(H):
                if (left>>np.uint64(c))&np.uint64(1):
                    flips[c,int((hb[t]>>np.uint64(c))&np.uint64(1))]+=1.
    return T/ns,flips/ns

@njit(cache=True)
def stay_probabilities(hb,op,bl,col,ded,H):
    """Probability a placed donor can remain for an independent next target."""
    stay=np.zeros((192,H+1))
    for k in range(192):
        if col[k]<0:continue
        for lo in range(col[k]+1):
            shown=op[k]&~((np.uint64(1)<<np.uint64(lo))-np.uint64(1))
            for t in range(256):
                own=ded[t]
                if own==k or ((shown>>np.uint64(col[own]))&np.uint64(1)):continue
                holes=shown&~op[own]
                if not ((bl[k]^hb[t])&holes):stay[k,lo]+=1./256
    return stay

def filler_features(aux,mode='filler'):
    hb,op,bl,col,ded,H,nc,nt,n1,p1,xy,freq=aux
    x,y=xy.T;demand=x+y
    samples=qmc_samples(H,16 if mode in ('stationary','persistent') else (32 if mode in ('fast','compact','stationary32') else 128))
    stay=stay_probabilities(hb,op,bl,col,ded,H) if mode=='persistent' else np.empty((0,0))
    out={};tf={}
    partnames=['raw','cost','fix','fill','fdig','covered','length','fix2']
    # A small predetermined physical parameter grid. Coefficients are learned
    # on training seeds; this extraction never opens observed costs.
    strengths=[2] if mode in ('fast','stationary','stationary32','persistent') else ([4] if mode=='compact' else [0,1,2,4])
    for strength in strengths:
        prob=(y+strength*nt*(y>x))/np.maximum(1,demand+strength*nt)
        covers,starts,utility,heads=donor_tables(hb,op,bl,col,ded,H,prob,freq)
        hp=np.array([utility[heads[c,0]]*(1-prob[c])+utility[heads[c,1]]*prob[c] for c in range(H)])
        out[f'f_s{strength}_headutility']=hp.sum()/256
        for price in ((1.6,) if mode in ('fast','stationary','stationary32','persistent') else ((1.,2.2) if mode=='compact' else (1.,1.6,2.2))):
            tag=f'f_s{strength}_p{price:g}'
            T,flips=cover_expectation(hb,op,bl,col,ded,H,prob,covers,starts,heads,samples,price,stay)
            for j,name in enumerate(partnames):
                tf[tag+'_'+name]=T[:,j]
                out[tag+'_'+name]=T[:,j].mean()
            for power in (2,3):out[tag+f'_moment{power}']=np.mean(T[:,1]**power)
            if mode in ('markov','stationary','stationary32','persistent') and strength in (0,2) and price==1.6:
                pcur=prob.copy()
                for step in range(1,3 if mode=='stationary32' else 5):
                    # Conditional transition rates: selection depends on the
                    # current head. Dividing by its probability avoids treating
                    # the surviving requests as an independent sample.
                    a=flips[:,1]/np.maximum(1e-4,1-pcur)
                    b=flips[:,0]/np.maximum(1e-4,pcur)
                    new=(a+strength*nt*(y>x))/np.maximum(1,a+b+strength*nt)
                    pcur=0.5*pcur+0.5*new
                    T,flips=cover_expectation(hb,op,bl,col,ded,H,pcur,covers,starts,heads,samples,price,stay)
                    mtag=f'm_s{strength}_it{step}'
                    for j,name in enumerate(partnames):
                        tf[mtag+'_'+name]=T[:,j]
                        out[mtag+'_'+name]=T[:,j].mean()
                    out[mtag+'_lastfix']=flips[-1].sum()/256
                    out[mtag+'_tailfix']=flips[-5:].sum()/256
    return out,tf

_WORKER_TABLE=None
_WORKER_MODE=None

def worker_init(table,mode):
    global _WORKER_TABLE,_WORKER_MODE
    _WORKER_TABLE=table;_WORKER_MODE=mode

def feature_row(st):
    out,t,aux=static_features(st,_WORKER_TABLE)
    if _WORKER_MODE!='static':
        more,mt=filler_features(aux,mode=_WORKER_MODE)
        out.update(more);t.update(mt)
    return list(out),np.array(list(out.values()),np.float32),list(t),np.column_stack(list(t.values())).astype(np.float32)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--mode',choices=['static','filler','markov','fast','compact','stationary','stationary32','persistent'],default='static')
    p.add_argument('--variants',nargs='*');p.add_argument('--force',action='store_true')
    p.add_argument('--jobs',type=int,default=12)
    a=p.parse_args();table=poset_table()
    for sf in sorted(DATA.glob('*.states.json')):
        tag=sf.name.removesuffix('.states.json')
        if a.variants and tag not in a.variants:continue
        dest=DATA/(tag+'.'+a.mode+'.npz')
        if dest.exists() and not a.force: continue
        states=json.loads(sf.read_text());DX=[];TX=[]
        print('extracting',tag,a.mode,'workers',a.jobs,flush=True)
        # Warm compilation in the parent; process workers reuse Numba's on-disk cache.
        worker_init(table,a.mode)
        first=feature_row(states[0]);names,dx,tnames,tx=first
        DX.append(dx);TX.append(tx)
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.jobs,initializer=worker_init,initargs=(table,a.mode)) as ex:
            for i,(nm,dx,tnm,tx) in enumerate(ex.map(feature_row,states[1:],chunksize=8),start=2):
                assert names==nm and tnames==tnm
                DX.append(dx);TX.append(tx)
                if i%100==0:print(tag,a.mode,i,flush=True)
        np.savez_compressed(dest,X=np.asarray(DX,dtype=np.float32),names=names,
                            T=np.asarray(TX,dtype=np.float32),tnames=tnames)
        print('saved',dest,flush=True)

if __name__=='__main__':main()
