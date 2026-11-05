from pathlib import Path
import subprocess,sys,json,re,statistics as st
p=Path(__file__).parent
stamp='20261106-064603'
names=['argon-des-perf-latew105','argon-req-k2late-v2','argon-req-k2late-isolate','argon-req-k2direct-isolate','argon-req-planscreen-v3']
runs=[stamp+'_'+s for s in names]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
root=Path('/home/sato/ahc074/runs')
a=root/runs[1];b=root/runs[2];n=0
for f in sorted(a.glob('out/*.txt'))+sorted(a.glob('orders/*/out/*.txt')):
 rel=f.relative_to(a);assert f.read_bytes()==(b/rel).read_bytes(),str(rel)
 e=rel.parent.parent/'err'/rel.name
 norm=lambda x:[s for s in x.splitlines() if not re.match(r'^\w+_sec = ',s)]
 assert norm((a/e).read_text())==norm((b/e).read_text()),str(e)
 n+=1
print('noinline exact stdout and non-time stderr',n)
for name in runs:
 rr=root/name;rows=[]
 for f in list(rr.glob('err/*.txt'))+list(rr.glob('orders/*/err/*.txt')):
  rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)})
 for r in rows:assert r.get('self_wrong',0)==r.get('op_label_errors',0)==0
 fields=[k for k in rows[0] if k.startswith(('joint_late_','raw_joint_','value_seed_'))]
 print(name,{k:st.mean(r[k] for r in rows) for k in fields},flush=True)
