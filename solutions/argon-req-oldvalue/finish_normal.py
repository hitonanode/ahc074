from pathlib import Path
import subprocess,re,statistics as st,json
base='20261106-020046_argon-des-perf-condbound';cand='20261106-020046_argon-req-completefast';p=Path('solutions/argon-req-completefast')
with p.joinpath('normal-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',base,cand,'--json',str(p/'normal-results.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
with p.joinpath('validation.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/check_final.py',base,cand,'20261106-015127_argon-req-completefast',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
root=Path('/home/sato/ahc074/runs');rows=[]
for f in (root/cand/'err').glob('*.txt'):
 rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)})
metrics={k:st.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('complete_value','value_filler'))}
p.joinpath('local-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
with p.joinpath('builds-final.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/check_builds.py',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Normal metrics, all saved-output checks, and final four builds complete.',flush=True)
