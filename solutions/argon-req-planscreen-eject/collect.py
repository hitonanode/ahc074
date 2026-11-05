from pathlib import Path
import re,statistics as st,subprocess,sys,json
p=Path(__file__).parent;r=Path('/home/sato/ahc074/runs')
stamp=re.search(r'run-id: (\d{8}-\d{6})_', (p/'smoke.log').read_text()).group(1)
names=['argon-des-perf-latew105','argon-req-planscreen-gap2','argon-req-planscreen-all','argon-req-planscreen-eject'];runs=[stamp+'_'+n for n in names]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
for name in runs:
 rr=r/name;rows=[]
 for f in sorted(rr.glob('err/*.txt'))+sorted(rr.glob('orders/*/err/*.txt')):
  d={k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)}
  assert d.get('self_wrong',0)==d.get('op_label_errors',0)==0
  rows.append(d)
 print(name,{k:st.mean(x[k] for x in rows) for k in rows[0] if k.startswith(('raw_joint_','value_seed_'))},flush=True)
