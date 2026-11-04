from pathlib import Path
import json,sys
folder=Path(__file__).resolve().parent
seed=int(sys.argv[1]);source=sys.argv[2]
data=(folder.parent/'triple-bound/models'/f'{seed:04}-groups.txt').read_text().split()
a=list(map(int,data[2:258]))
if source=='base':
    lines=Path(f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt').read_text().splitlines()[:192]
    physical=[j for j in range(63)if any(lines[k][j]!='.'for k in range(1,7))]
    edges=[]
    for j in physical:
        xy=[k-1 for k in range(1,7)if lines[k][j]!='.'];assert len(xy)==2
        edges.append([*xy,int(lines[xy[0]+1][j])])
    edges += [None]*(63-len(edges));m=6
else:
    d=json.loads(Path(source).read_text());edges=d['edges'];m=d['M']
windows=[j for j,e in enumerate(edges)if e is not None]+[j for j,e in enumerate(edges)if e is None]
G=sum(e is not None for e in edges)
print(m,G)
for value in a:print(sum(((value>>j)&1)<<k for k,j in enumerate(windows)))
for j in windows[:G]:print(*edges[j])
