from pathlib import Path
import re,statistics as st,subprocess,sys,json
p=Path(__file__).parent;r=Path('/home/sato/ahc074/runs');stamp='20261106-071202'
names=['argon-des-perf-latew105','argon-req-midrepair-probe'];runs=[stamp+'_'+n for n in names]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
base=r/runs[0];rr=r/runs[1];rows=[];per_order=[]
for f in sorted(rr.glob('out/*.txt'))+sorted(rr.glob('orders/*/out/*.txt')):
 rel=f.relative_to(rr);assert f.read_bytes()==(base/rel).read_bytes(),str(rel)
 e=rel.parent.parent/'err'/rel.name;a=(rr/e).read_text();b=(base/e).read_text()
 norm=lambda s:[l for l in s.splitlines() if l.startswith(('@paper','@ops'))]
 assert norm(a)==norm(b),str(e)
 rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',a,re.M)})
 for line in a.splitlines():
  if line.startswith('#midorder '):per_order.append(list(map(float,line.split()[1:])))
print('identical stdout/paper/ops files',len(rows),flush=True)
fields=[k for k in rows[0] if k.startswith('mid_')]
means={k:st.mean(x[k] for x in rows) for k in fields};(p/'metrics.json').write_text(json.dumps(means,indent=2)+'\n')
print('means',means,flush=True)
print('orders',len(per_order),'illegal',sum(x[2]>0 for x in per_order),'exposable',sum(x[3]>0 for x in per_order),'repairable',sum(x[4]>0 for x in per_order),'new_gain',sum(x[6]>1e-9 for x in per_order),'max_order_gain',max(x[6] for x in per_order),flush=True)
