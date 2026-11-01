"""Reproduce canonicalize's interpretation of stored post-request orders.
Distinguishes persistent interior fillers from level-zero helper papers.
"""
import json
from collections import Counter
from analyze import load, mean_se

rows=[]
for seed in range(8):
    inp,out,gm,hs,cols,serves=load(seed)
    order=list(range(192));s=Counter()
    for ops in out.queries:
        for k,d in ops:order.remove(k);order.insert(d,k)
        cur=28;gen_seen=False;fillers=[]
        for i in range(191,-1,-1):
            k=order[i];c=cols[k]
            if c<0:
                gen_seen=True
                continue
            if not gen_seen and c<=cur:cur=c
            elif i!=0:fillers.append((k,0 if gen_seen else min(cur,c),c,gen_seen))
        s['fillers']+=len(fillers)
        s['positive_level_fillers']+=sum(level>0 for k,level,c,gen in fillers)
        intra=[f for f in fillers if not f[3] and f[1]<f[2] and f[1]//3==f[2]//3]
        s['intra_triple_fillers']+=len(intra)
        s['queries_with_intra_triple_fillers']+=bool(intra)
    rows.append(dict(seed=seed,**{k:v/1024 for k,v in s.items()}))
print(json.dumps(dict(seed_rows=rows,mean_and_se={k:mean_se([r[k] for r in rows]) for k in rows[0] if k!='seed'}),indent=2))
