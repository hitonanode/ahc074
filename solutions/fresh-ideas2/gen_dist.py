# Mean distance between orders of 6 generic sheets: legal moves (bottom sheet not movable) vs any sheet.
import itertools, collections
M=6
perms=list(itertools.permutations(range(M)))
idx={p:i for i,p in enumerate(perms)}
def nbrs(p, legal):
    out=[]
    for pos in range(M - (1 if legal else 0)):
        for d in range(M):
            if d==pos: continue
            q=list(p); k=q.pop(pos); q.insert(d,k); out.append(idx[tuple(q)])
    return out
for legal in (True, False):
    adj=[nbrs(p,legal) for p in perms]
    tot=0; mx=0
    for s in range(len(perms)):
        dist=[-1]*len(perms); dist[s]=0; dq=collections.deque([s])
        while dq:
            x=dq.popleft()
            for y in adj[x]:
                if dist[y]<0: dist[y]=dist[x]+1; dq.append(y)
        tot+=sum(dist); mx=max(mx,max(dist))
    print('legal' if legal else 'free ', 'mean dist', tot/len(perms)**2, 'max', mx)
