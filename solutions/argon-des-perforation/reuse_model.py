"""Optimistic static marginal model for perforating the previous product.

No actual future orders enter the model. Cost is the existing hole-cost model,
so this is a model envelope, not a mathematical upper bound on the full score.
"""
import argparse, itertools, json, math, statistics
from pathlib import Path
from exposure import load_design, static_heads
HERE=Path(__file__).resolve().parent

def probe(seed,run,max_holes):
    inp,d=load_design(seed,run);rank,_,_,_=static_heads(d)
    H=d['H'];cols=d['columns'];ded=d['ded'];served=[[]for _ in range(192)]
    for u,k in enumerate(ded):served[k].append(u)
    def hb(bits):return sum(((bits>>h)&1)<<j for j,h in enumerate(d['handle']))
    target=[hb(x)for x in d['A']];opacity=[hb(d['papers'][2*k])for k in range(192)]
    colors=[hb(d['papers'][2*k+1])for k in range(192)]
    counts=[[0,0]for _ in range(H)];demands=[0]*H
    for u in range(256):
        demands[cols[ded[u]]]+=1
        for c in range(H):
            if not opacity[ded[u]]>>c&1:counts[c][target[u]>>c&1]+=1
    prob=[]
    for c,(x,y)in enumerate(counts):
        reset=2*demands[c];p=(y+reset*(y>x))/(x+y+reset);prob.append([1-p,p])
    bad=[[prob[c][(target[u]>>c&1)^1]for c in range(H)]for u in range(256)]
    def gain(u,k,opq):
        # Relax placement costs and accessibility, including the donor's own handle.
        mask=opq&~opacity[ded[u]]&((1<<(cols[k]+1))-1)
        wrong=mask&(colors[k]^target[u]);lo=wrong.bit_length();cover=mask&~((1<<lo)-1)
        v=0.
        while cover:
            bit=cover&-cover;cover-=bit;v+=bad[u][bit.bit_length()-1]
        return v
    candidates=[];trials=0;improved_reuse=0;best_net=1e9;max_benefit=0
    for k in range(7,192):
        if rank[k]==0:continue
        old=[gain(u,k,opacity[k])for u in range(256)]
        bits=opacity[k]&((1<<cols[k])-1);allowed=[];price_of={}
        while bits:
            bit=bits&-bits;bits-=bit;c=bit.bit_length()-1
            x,y=counts[c];reset=2*demands[c]
            cost=lambda x,y:1.52*(x*y+.5*reset*min(x,y))/max(1,x+y+reset)
            freq=len(served[k]);nx=x+sum(not(target[u]>>c&1)for u in served[k]);ny=y+sum(target[u]>>c&1 for u in served[k])
            price=cost(nx,ny)-cost(x,y)
            allowed.append(c);price_of[c]=price
        for width in range(1,max_holes+1):
            for holes in itertools.combinations(allowed,width):
                mask=sum(1<<c for c in holes);price=sum(price_of[c]for c in holes)
                benefit=len(served[k])/255*sum(gain(u,k,opacity[k]^mask)-old[u]for u in range(256))
                trials+=1;improved_reuse+=benefit>0;best_net=min(best_net,(price-benefit)/256);max_benefit=max(max_benefit,benefit/256)
                if benefit>price:candidates.append(dict(k=k,handles=holes,rank=rank[k],benefit=benefit,price=price,net=(price-benefit)/256))
    return dict(seed=seed,count=len(candidates),trials=trials,improved_reuse=improved_reuse,best_net=best_net,max_benefit=max_benefit,
                optimistic_net=sum(x['net']for x in candidates),candidates=candidates)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='20261105-151134_esw-slim');p.add_argument('--end',type=int,default=100)
    p.add_argument('--max-holes',type=int,default=1);p.add_argument('--output',default='reuse-model.json')
    a=p.parse_args();rows=[]
    for seed in range(a.end):
        rows.append(probe(seed,a.run,a.max_holes))
        if len(rows)%20==0:print('done',len(rows),flush=True)
    vals=[r['optimistic_net']for r in rows]
    summary=dict(n=len(rows),mean=statistics.mean(vals),se=statistics.stdev(vals)/math.sqrt(len(vals)),
                 candidates=statistics.mean(r['count']for r in rows),changed=sum(bool(r['count'])for r in rows),
                 trials=sum(r['trials']for r in rows),improved_reuse=sum(r['improved_reuse']for r in rows),
                 best_net=min(r['best_net']for r in rows),max_benefit=max(r['max_benefit']for r in rows))
    (HERE/a.output).write_text(json.dumps(dict(summary=summary,rows=rows),indent=2)+'\n')
    print(json.dumps(summary))
if __name__=='__main__':main()
