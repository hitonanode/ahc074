"""保存済み出力だけを分析する。whenidle.shから1コアで実行する。"""
import collections, itertools, json, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import replay
import numpy as np
import networkx as nx
run=Path('/home/sato/ahc074/runs')/sys.argv[1]
limit=int(sys.argv[2]) if len(sys.argv)>2 else 50
rows=[]
for seed in range(limit):
    inp=replay.load_input(seed)
    out=replay.parse_output(inp,(run/'out'/f'{seed:04d}.txt').read_text())
    ann=replay.parse_annotations((run/'err'/f'{seed:04d}.txt').read_text(),inp.k)
    if len(out.designs)!=192: continue
    paper=out.designs
    owners=[[int(u) for u in x.split(',')] if x!='-' else [] for x in ann.papers['targets']]
    bg=[k for k in range(1,192) if ann.papers['col'][k]=='0']
    if len(bg)!=6: continue
    owner=[owners[k][0] for k in bg]
    # Rules 1-2 are checked on all windows, without treating cap-hidden ink as exempt.
    violations=sum(((paper[k].black^inp.target[u])&paper[k].opaque).bit_count() for k in range(1,192) for u in owners[k])
    freedom=[]
    for w in range(63):
        ones=sum((inp.target[u]>>w)&1 for u in owner)
        freedom.append(ones*(6-ones))
    ui,vi=np.triu_indices(256,1)
    a=np.array(inp.target,dtype=np.uint64)[ui]
    d=a^np.array(inp.target,dtype=np.uint64)[vi]
    samecap=(d & np.uint64(1<<63))==0
    distance=np.bitwise_count(d)
    relation=np.zeros(len(a),dtype=np.uint64)
    for x,y in itertools.combinations(range(6),2):
        m=paper[bg[x]].opaque & paper[bg[y]].opaque & ((1<<63)-1)
        assert all(sum((paper[k].opaque>>w)&1 for k in bg)==2 for w in range(63) if (m>>w)&1)
        q=d & np.uint64(m)
        wrong=a^np.uint64(paper[bg[x]].black)
        relation |= np.where((q & ~wrong)!=0, np.uint64(1<<(8*x+y)),np.uint64(0))
        relation |= np.where((q & wrong)!=0,np.uint64(1<<(8*y+x)),np.uint64(0))
    for k in range(6):
        reach=(relation >> np.uint64(8*k)) & np.uint64(63)
        for i in range(6):
            relation |= np.where((relation & np.uint64(1<<(8*i+k)))!=0,reach << np.uint64(8*i),np.uint64(0))
    feasible=(relation & np.uint64(sum(1<<(9*i) for i in range(6))))==0
    g=nx.Graph();g.add_nodes_from(range(256));g.add_edges_from(zip(ui[feasible&samecap],vi[feasible&samecap]))
    rows.append(dict(seed=seed, owner_violations=violations, freedom=statistics.mean(freedom), compatible=int(feasible.sum()),samecap_compatible=int((feasible&samecap).sum()),samecap_short26=int((feasible&samecap&(distance<=26)).sum()),samecap_short28=int((feasible&samecap&(distance<=28)).sum()), samecap_max_matching=len(nx.max_weight_matching(g,maxcardinality=True))))
print(json.dumps({'run':run.name,'seeds':len(rows),'mean':{k:statistics.mean(r[k] for r in rows) for k in rows[0] if k!='seed'},'rows':rows},indent=2))
