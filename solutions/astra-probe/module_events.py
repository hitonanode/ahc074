"""Aggregate the current top-paper masks into an intentionally relaxed 6-card workload.
Display and exposure events are separate iid events; actual extraction and long
queues are NOT modeled. Frequencies per original global request sum to event_rate.
"""
from collections import Counter
from analyze import load

counts=[Counter() for _ in range(9)]
for seed in range(8):
    inp,out,gm,hs,cols,serves=load(seed)
    ded={u:k for k,us in serves.items() for u in us}
    for b in range(9):
        for u,a in enumerate(inp.target):
            k=ded[u]
            mask=sum((not(out.designs[k].opaque >> hs[3*b+j] & 1)) << j for j in range(3))
            bits=sum((a >> hs[3*b+j] & 1) << j for j in range(3))
            if mask: counts[b][(mask,bits&mask)] += 1
            if 3*b <= cols[k] < 3*b+3:
                j=cols[k]-3*b
                counts[b][(0,2*j+(bits>>j&1))] += 1
for b,cc in enumerate(counts):
    print(b,len(cc))
    for (mask,bits),count in sorted(cc.items()):
        print(mask,bits,count/(8*256))
