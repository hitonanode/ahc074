from pathlib import Path
import re,statistics as st,subprocess,sys,json
p=Path(__file__).parent;r=Path('/home/sato/ahc074/runs');stamp=re.search(r'run-id: (\d{8}-\d{6})_', (p/'smoke.log').read_text()).group(1)
runs=[stamp+'_'+n for n in ['argon-des-perf-latew105','argon-req-helperkeep-probe']]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
base=r/runs[0];rr=r/runs[1];rows=[]
for f in sorted(rr.glob('out/*.txt'))+sorted(rr.glob('orders/*/out/*.txt')):
 rel=f.relative_to(rr);assert f.read_bytes()==(base/rel).read_bytes(),str(rel)
 e=rel.parent.parent/'err'/rel.name;a=(rr/e).read_text();b=(base/e).read_text()
 norm=lambda s:[l for l in s.splitlines() if l.startswith(('@paper','@ops'))]
 assert norm(a)==norm(b),str(e)
 rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',a,re.M)})
means={k:st.mean(x[k] for x in rows) for k in rows[0] if k.startswith('helper_probe_')}
(p/'metrics.json').write_text(json.dumps(means,indent=2)+'\n')
print('identical stdout/paper/ops files',len(rows),flush=True)
print('per-order max gains',[means[f'helper_probe_best_{g}'] for g in range(4)],flush=True)
for stage in range(3):
 for gate in range(4):
  prefix=f'helper_probe_{stage}_{gate}_'
  print(stage,gate,{k.removeprefix(prefix):v for k,v in means.items() if k.startswith(prefix)},flush=True)
