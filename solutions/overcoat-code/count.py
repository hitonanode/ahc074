from pathlib import Path
import sys,json,statistics
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'scripts'));import replay
run=replay.resolve_run('20261103-033246_as6-canon');rows=[]
for seed in range(24,88):
 inp=replay.load_input(seed);out=replay.parse_output(inp,(run/'out'/f'{seed:04d}.txt').read_text());a=inp.target;products=[];minimum=[]
 for i in range(1,7):
  p=out.designs[i];dist=[((p.black^t)&p.opaque).bit_count()for t in a if t>>63&1];minimum.append(min(dist));products += [(i,u)for u,t in enumerate(a)if t>>63&1 and not((p.black^t)&p.opaque)]
 rows.append(dict(seed=seed,eligible=products,minimum=minimum))
(root/'solutions/overcoat-code/count.json').write_text(json.dumps(rows,indent=2)+'\n')
print('cases',len(rows),'mean exact matches',statistics.mean(len(r['eligible'])for r in rows),'cases with match',sum(bool(r['eligible'])for r in rows))
print('minimum per paper', {i:sum(x==i for r in rows for x in r['minimum'])for i in range(8)})
