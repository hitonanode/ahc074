from pathlib import Path
import sys,subprocess,json
sys.path.insert(0,str(Path('scripts').resolve()))
import replay
base,cand=sys.argv[1:];root=Path('/home/sato/ahc074/runs');a=root/base;b=root/cand
ca=replay.run_scores(a);cb=replay.run_scores(b)
seeds=sorted(ca.keys()&cb.keys(),key=lambda s:cb[s]-ca[s])
subprocess.run(['python3','scripts/observe.py','cases',cand,'--vs',base,'--top','3'],check=True)
for seed in [seeds[0],seeds[-1]]:
 inp=replay.load_input(seed);oa=replay.parse_output(inp,replay.out_path(a,seed).read_text());ob=replay.parse_output(inp,replay.out_path(b,seed).read_text())
 ga=replay.Game(inp,oa.designs);gb=replay.Game(inp,ob.designs);parts=[];start=None;delta=0
 for r,(qa,qb) in enumerate(zip(oa.queries,ob.queries)):
  was_same=ga.order==gb.order
  for k,d in qa:ga.move(k,d)
  for k,d in qb:gb.move(k,d)
  assert ga.finish(r) and gb.finish(r)
  if start is None and (qa!=qb):start=r;delta=0
  if start is not None:
   delta+=len(qb)-len(qa)
   if ga.order==gb.order:
    parts.append((start,r,delta));start=None
 if start is not None:parts.append((start,len(oa.queries)-1,delta))
 print('SEED',seed,'score delta',cb[seed]-ca[seed],'episodes',parts,flush=True)
 if not parts:continue
 selected=min(parts,key=lambda p:p[2]) if cb[seed]<ca[seed] else max(parts,key=lambda p:p[2])
 r=selected[0];print('SELECTED',seed,selected,flush=True)
 for run in [base,cand]:
  subprocess.run(['python3','scripts/observe.py','queries',run,str(seed),'--from',str(r),'--to',str(r+2),'--attr','role,col'],check=True)
  subprocess.run(['python3','scripts/observe.py','state',run,str(seed),'--request',str(r),'--after'],check=True)
 subprocess.run(['python3','scripts/observe.py','stats',cand,'--vs',base,'--seed',str(seed)],check=True)
