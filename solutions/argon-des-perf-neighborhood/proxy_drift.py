"""Perforation's effect on the analytic head probabilities and filler utilities."""
import collections, json, math, statistics
from pathlib import Path
from exposure import load_design
HERE=Path(__file__).resolve().parent
exposure=json.loads((HERE/'exposure-new200.json').read_text())
rows=[]
for saved in exposure['rows']:
    seed=saved['seed'];_,d=load_design(seed,exposure['run']);H=d['H'];col=d['columns'];ded=d['ded']
    owners=[[]for _ in range(192)]
    for u,k in enumerate(ded):owners[k].append(u)
    target=[sum((a>>h&1)<<c for c,h in enumerate(d['handle']))for a in d['A']]
    old=[0]*192;new=[0]*192;colors=[0]*192;demand=[0]*H
    for k in range(7,192):
        u,v=owners[k][0],owners[k][-1];c=col[k]
        old[k]=((1<<(c+1))-1)&~(target[u]^target[v]);colors[k]=target[u]
        new[k]=sum((d['papers'][2*k]>>h&1)<<j for j,h in enumerate(d['handle']))
        assert not new[k]&~old[k]
        demand[c]+=len(owners[k])
    def probs(opacity):
        counts=[[0,0]for _ in range(H)]
        for u,k in enumerate(ded):
            for c in range(H):
                if not opacity[k]>>c&1:counts[c][target[u]>>c&1]+=1
        p=[(y+2*demand[c]*(y>x))/(x+y+2*demand[c]) for c,(x,y)in enumerate(counts)]
        return p,counts
    p0,n0=probs(old);p1,n1=probs(new)
    observed=[0.]*H;total=[0]*H
    for k in range(7,192):
        c=col[k];total[c]+=saved['top'][k];observed[c]+=saved['top'][k]*(colors[k]>>c&1)
    observed=[a/b if b else .5 for a,b in zip(observed,total)]
    heads=[[next(k for k in range(7,192)if col[k]==c and saved['rank'][k]==0 and (colors[k]>>c&1)==b)for b in [0,1]]for c in range(H)]
    def utilities(opacity,prob):
        utility=[0.]*192
        for k in range(7,192):
            c=col[k]
            # Only maximum-frequency papers may become the head.
            if len(owners[k])<len(owners[heads[c][colors[k]>>c&1]]):continue
            for u in range(256):
                if c==col[ded[u]]:continue
                mask=opacity[k]&~opacity[ded[u]];lo=((colors[k]^target[u])&mask).bit_length()
                if lo>=c:continue
                cover=mask&((1<<c)-1)&~((1<<lo)-1);z0=1.;z1=0.;expected=0.
                while cover:
                    bit=cover&-cover;cover-=bit;j=bit.bit_length()-1
                    p=prob[j] if not target[u]>>j&1 else 1-prob[j]
                    expected+=p;z1=z1*(1-p)+z0*p;z0*=1-p
                utility[k]+=max(0.,expected-(1-z0)-.6*(1-z0-z1))
        return utility
    u0=utilities(old,p0);u1=utilities(new,p0);u2=utilities(new,p1)
    value=lambda utility,prob,head:sum((1-prob[c])*utility[head[c][0]]+prob[c]*utility[head[c][1]]for c in range(H))/256
    def rerank(utility):
        return [[max((k for k in range(7,192)if col[k]==c and (colors[k]>>c&1)==b),key=lambda k:(len(owners[k]),utility[k],-k))for b in [0,1]]for c in range(H)]
    # Match the earlier-stage proxy: exclude the target's own column and
    # choose its best head consistently before/after (not Perforation's head ranking).
    heads=rerank(u0)
    head2=rerank(u2)
    shifts=[abs(x-y)for x,y in zip(p0,p1)]
    rows.append(dict(seed=seed,holes=sum((x&~y).bit_count()for x,y in zip(old,new)),prob_mean=statistics.mean(shifts),prob_max=max(shifts),
        majority_flips=sum((x[1]>x[0])!=(y[1]>y[0])for x,y in zip(n0,n1)),
        head_changes=sum(x!=y for a,b in zip(heads,head2)for x,y in zip(a,b)),
        proxy_before=value(u0,p0,heads),proxy_after_fixedprob=value(u1,p0,heads),proxy_after=value(u2,p1,heads),proxy_after_rerank=value(u2,p1,head2),
        probability_mse_before=statistics.mean((p-o)**2 for p,o in zip(p0,observed)),probability_mse_after=statistics.mean((p-o)**2 for p,o in zip(p1,observed))))
    if len(rows)%20==0:print('done',len(rows),flush=True)
summary={k:dict(mean=statistics.mean(r[k]for r in rows),max=max(r[k]for r in rows))for k in rows[0]if k!='seed'}
(HERE/'proxy-drift200.json').write_text(json.dumps(dict(run=exposure['run'],n=len(rows),summary=summary,rows=rows),indent=2)+'\n')
print(json.dumps(summary,indent=2))
