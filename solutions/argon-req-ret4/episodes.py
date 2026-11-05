from pathlib import Path
import sys,json
sys.path.insert(0,str(Path('scripts').resolve()))
import replay
root=Path('/home/sato/ahc074/runs')
b=root/'20261105-222520_esw-slim';c=root/'20261105-222520_argon-req-ret4'
results=[]
for seed in [64,710,36,1883]:
 inp=replay.load_input(seed)
 bo=replay.parse_output(inp,(b/'out'/f'{seed:04d}.txt').read_text());co=replay.parse_output(inp,(c/'out'/f'{seed:04d}.txt').read_text())
 bg=replay.Game(inp,bo.designs);cg=replay.Game(inp,co.designs)
 first=None;events=[];active=None
 for r,(bp,cp) in enumerate(zip(bo.queries,co.queries)):
  if bp!=cp and first is None:first=r
  if bp!=cp and active is None:active={'from':r,'gain':0,'first_base_moves':len(bp),'first_candidate_moves':len(cp)}
  for k,d in bp:bg.move(k,d)
  for k,d in cp:cg.move(k,d)
  assert bg.finish(r) and cg.finish(r)
  if active is not None:
   active['gain']+=len(bp)-len(cp)
   if bg.order==cg.order:
    active['to']=r;events.append(active);active=None
 if active:active['to']=1023;events.append(active)
 results.append({'seed':seed,'first_difference':first,'total_gain':sum(len(x)-len(y) for x,y in zip(bo.queries,co.queries)),'episodes':events})
print(json.dumps(results,indent=2))
