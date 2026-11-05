from pathlib import Path
import re,statistics as st,subprocess,sys,json
p=Path(__file__).parent;r=Path('/home/sato/ahc074/runs');stamp=re.search(r'run-id: (\d{8}-\d{6})_', (p/'smoke.log').read_text()).group(1)
names=['argon-des-perf-latew105','argon-req-collectonce','argon-req-planscreen-probe'];runs=[stamp+'_'+n for n in names]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
base=r/runs[0]
for j,name in enumerate(runs[1:]):
 rr=r/name;n=0;rows=[]
 for f in sorted(rr.glob('out/*.txt'))+sorted(rr.glob('orders/*/out/*.txt')):
  rel=f.relative_to(rr);assert f.read_bytes()==(base/rel).read_bytes(),(name,str(rel))
  e=rel.parent.parent/'err'/rel.name;a=(rr/e).read_text();b=(base/e).read_text()
  if j==0:
   norm=lambda s:[l for l in s.splitlines() if not re.match(r'^\w+_sec = ',l)]
  else:
   norm=lambda s:[l for l in s.splitlines() if l.startswith(('@paper','@ops'))]
  assert norm(a)==norm(b),(name,str(e))
  rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',a,re.M)})
  n+=1
 print(name,'identical files',n,flush=True)
 if j==1:
  metrics={k:st.mean(x[k] for x in rows) for k in rows[0] if k.startswith('extra_probe_')}
  (p/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
  for stage in range(2):
   for gate in range(6):
    prefix=f'extra_probe_{stage}_{gate}_'
    print(stage,gate,{k.removeprefix(prefix):v for k,v in metrics.items() if k.startswith(prefix)},flush=True)
