"""単独少数色紙が fix に使われる頻度。保存済み注釈と出力を読むだけ。"""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
import replay

run=Path('/home/sato/ahc074/runs/20261109-003105_dcomp-combo-dual30')
totals=Counter(); by_column=[Counter() for _ in range(25)]; depths=Counter()
examples=[]
for seed in range(50):
    inp=replay.load_input(seed)
    out=replay.parse_output(inp,(run/'out'/f'{seed:04d}.txt').read_text())
    ann=replay.parse_annotations((run/'err'/f'{seed:04d}.txt').read_text(),inp.k)
    col=[int(x) if x!='-' else -1 for x in ann.papers['col']]
    color=[int(x) if x!='-' else -1 for x in ann.papers['hcolor']]
    groups={(c,b):[] for c in range(25) for b in range(2)}
    for k,c in enumerate(col):
        if c>=0: groups[c,color[k]].append(k)
    lone={v[0] for (c,b),v in groups.items() if len(v)==1 and len(groups[c,b^1])>1}
    lonecols={col[k] for k in lone}
    for k in lone:
        depth=int(ann.papers['depth0'][k]);depths[depth]+=1
        totals['lone_initial_depth_sum']+=depth
        totals['lone_column_size_sum']+=len(groups[col[k],0])+len(groups[col[k],1])
    totals['lone_columns']+=len(lonecols)
    for c in lonecols: by_column[c]['lone_cases']+=1
    for r,ops in enumerate(out.queries):
        for (k,d),label in zip(ops,ann.labels_of(r,len(ops))):
            c=col[k]
            if c<0: continue
            totals['moves']+=1
            if label=='fix':
                totals['fix_moves']+=1
                if c in lonecols: by_column[c]['lone_column_fix_moves']+=1
            if k in lone:
                by_column[c]['lone_moves']+=1
                by_column[c]['lone_'+label]+=1
                totals['lone_'+label]+=1
                if label=='fix' and len(examples)<12: examples.append({'seed':seed,'request':r,'paper':k,'column':c})

result={'run':run.name,'seeds':'0-49','totals':dict(totals),'by_column':[dict(x) for x in by_column],
        'examples':examples,'lone_columns_per_case':totals['lone_columns']/50,
        'lone_fix_moves_per_order':totals['lone_fix']/(50*1024),
        'lone_fix_moves_per_order_shallow20':sum(x['lone_fix'] for x in by_column[:20])/(50*1024),
        'lone_initial_depth_mean':totals['lone_initial_depth_sum']/totals['lone_columns'],
        'lone_column_size_mean':totals['lone_column_size_sum']/totals['lone_columns'],
        'lone_initial_depth_histogram':dict(sorted(depths.items()))}
print(json.dumps(result,ensure_ascii=False,indent=2))
