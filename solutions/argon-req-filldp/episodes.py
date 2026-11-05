from pathlib import Path
import sys,json,re,subprocess
sys.path.insert(0,str(Path('scripts').resolve()))
import replay
root=Path('/home/sato/ahc074/runs')
b=root/'20261105-234921_esw-slim';c=root/'20261105-234921_argon-req-filldp-positive'
probe=root/'20261105-235342_argon-req-filldp-oracle'
for seed in [95,180]:
 inp=replay.load_input(seed)
 bo=replay.parse_output(inp,(b/'out'/f'{seed:04d}.txt').read_text());co=replay.parse_output(inp,(c/'out'/f'{seed:04d}.txt').read_text())
 bg=replay.Game(inp,bo.designs);cg=replay.Game(inp,co.designs)
 values={int(k):float(v) for k,v in re.findall(r'^r2_oracle_value_(\d+) = ([-+\d.eE]+)$',(probe/'err'/f'{seed:04d}.txt').read_text(),re.M)}
 active=None;events=[]
 for r,(bp,cp) in enumerate(zip(bo.queries,co.queries)):
  if bp!=cp and active is None:active={'from':r,'gain':0,'first_base_moves':len(bp),'first_candidate_moves':len(cp),'baseline_oracle_gain':values.get(r,0)}
  for k,d in bp:bg.move(k,d)
  for k,d in cp:cg.move(k,d)
  assert bg.finish(r) and cg.finish(r)
  if active is not None:
   active['gain']+=len(bp)-len(cp)
   if bg.order==cg.order:active['to']=r;events.append(active);active=None
 if active:active['to']=1023;events.append(active)
 print(json.dumps({'seed':seed,'gain':sum(x['gain'] for x in events),'events':events},indent=2),flush=True)
 focus=min(events,key=lambda x:x['gain']) if seed==95 else max(events,key=lambda x:x['gain'])
 r=focus['from'];end=min(1024,r+3)
 for run in [b.name,c.name]:
  subprocess.run(['python3','scripts/observe.py','queries',run,str(seed),'--from',str(r),'--to',str(end)],check=True)
  subprocess.run(['python3','scripts/observe.py','state',run,str(seed),'--request',str(r),'--after'],check=True)
 subprocess.run(['python3','scripts/observe.py','stats',c.name,'--vs',b.name,'--seed',str(seed)],check=True)
