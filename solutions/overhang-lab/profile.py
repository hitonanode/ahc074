from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"scripts"))
import replay

seed=int(sys.argv[1]);selected=list(map(int,sys.argv[2].split(",")));width=len(selected)
run=replay.resolve_run("20261103-230624_post-repair")
inp=replay.load_input(seed);out=replay.parse_output(inp,(run/"out"/f"{seed:04d}.txt").read_text())
papers=out.designs;gm=0
for p in papers[1:7]:gm|=p.opaque
cap=papers[0].opaque;hm=((1<<64)-1)^(gm|cap)
handles=[]
for p in papers[7:]:
    for j in range(64):
        if (hm&p.opaque)>>j&1 and j not in handles:handles.append(j)
cols={x:max(c for c,j in enumerate(handles) if papers[x].opaque>>j&1) for x in range(7,192)}
owners={x:[u for u,t in enumerate(inp.target) if not ((papers[x].black^t)&papers[x].opaque&~cap)] for x in cols}
owner={u:x for x,us in owners.items() for u in us}
local=[x for x in cols if cols[x] in selected];index={x:i for i,x in enumerate(local)}
windows=[handles[c]for c in selected]
bits=lambda x:sum(((x>>j)&1)<<i for i,j in enumerate(windows))
print(len(local),256,width)
for x in local:
    colors=[bits(inp.target[u]) for u in owners[x]]
    allowed=(1<<width)-1
    for c in colors:allowed&=~(colors[0]^c)
    print(x,selected.index(cols[x]),bits(papers[x].opaque),colors[0],allowed)
for u,t in enumerate(inp.target):
    x=owner[u]
    print(index.get(x,-1),bits(~papers[x].opaque),bits(t))
