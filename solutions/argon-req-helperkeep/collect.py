from pathlib import Path
import re,statistics as st,subprocess,sys,json
p=Path(__file__).parent;r=Path('/home/sato/ahc074/runs');stamp='20261106-071731'
runs=[stamp+'_'+n for n in ['argon-des-perf-latew105','argon-req-helperkeep']]
subprocess.run([sys.executable,'solutions/argon-req-completeold/analyze.py',*runs,'--end','200','--json',str(p/'results.json')],check=True)
rows=[]
rr=r/runs[1]
for f in list(rr.glob('err/*.txt'))+list(rr.glob('orders/*/err/*.txt')):
 d={k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)}
 assert d.get('self_wrong',0)==d.get('op_label_errors',0)==0;rows.append(d)
means={k:st.mean(x[k] for x in rows) for k in rows[0] if k.startswith('helper_keep_')}
(p/'metrics.json').write_text(json.dumps(means,indent=2)+'\n');print(means,flush=True)
