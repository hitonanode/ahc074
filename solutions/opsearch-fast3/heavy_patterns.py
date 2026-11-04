"""Classify recorded heavy rewrites by their removed papers' end visibility."""
from pathlib import Path
import sys, json
from collections import Counter
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay
root=Path('/home/sato/ahc074/runs/20261105-030311_heavy-mdp')
counts=Counter(); labels=Counter(); examples=[]
for seed in range(8):
    inp=replay.load_input(seed)
    out=replay.parse_output(inp,(root/'out'/f'{seed:04d}.txt').read_text())
    traces={}
    for line in (root/'err'/f'{seed:04d}.txt').read_text().splitlines():
        if line.startswith('#heavy '):
            t=line.split()
            if t[3]=='22.direct' and t[4]=='1': traces[int(t[1])]=t
    game=replay.Game(inp,out.designs)
    for r,path in enumerate(out.queries):
        if r in traces:
            t=traces[r]
            def parse(x): return [] if x=='-' else [(int(k),int(d),tag) for k,d,tag in (v.split(':') for v in x.split(','))]
            before,after=parse(t[11]),parse(t[12])
            bc,ac=Counter(k for k,d,l in before),Counter(k for k,d,l in after)
            rm=list((bc-ac).elements());add=list((ac-bc).elements())
            if len(rm)==len(add) and len(rm) in (1,2):
                order=game.order.copy()
                for k,d,l in before:order.remove(k);order.insert(d,k)
                visible=set(); cover=0
                for k in order:
                    opaque=game.papers[k].opaque
                    if opaque & ~cover:visible.add(k)
                    cover|=opaque
                owners=sum(k in visible for k in rm)
                counts[(len(rm),owners)]+=1
                removed_labels=tuple(sorted(l for k,d,l in before if k in rm))
                labels[(len(rm),owners,removed_labels)]+=1
                if owners<2 and len(examples)<10:examples.append({'seed':seed,'request':r,'owners':owners,'removed':rm,'added':add,'labels':removed_labels,'gain':float(t[5])-float(t[6])})
        for k,d in path:game.move(k,d)
        assert game.finish(r)
report={'source':root.name,'seeds':'0-8','two_to_two_removed_owners':{str(k):v for k,v in counts.items()},'labels':{str(k):v for k,v in labels.most_common()},'examples':examples}
Path('solutions/opsearch-fast3/heavy-patterns.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
