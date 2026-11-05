from pathlib import Path
import subprocess
root=Path('solutions/argon-req-k2-v3')
r='20261106-054848_'
names=['argon-req-ejectstats-v2','argon-req-k2-v3','argon-req-k2local-v3','argon-req-k2-probe','argon-req-k2local-probe','argon-req-seedfinish']
with (root/'screen-analysis.log').open('w') as out:
 subprocess.run(['python3','solutions/argon-req-completeold/analyze.py',*[r+n for n in names],'--end','200','--json',str(root/'screen-results.json')],stdout=out,check=True)
with (root/'oracle-analysis.log').open('w') as out:
 subprocess.run(['python3','solutions/argon-req-oldfull-v2/analyze_oracles.py',r+names[0],r+names[3],r+names[4],'--json',str(root/'oracle-results.json')],stdout=out,check=True)
print('K2 analysis passed',flush=True)
import json, re, statistics
results={}
for name in names:
 directory=Path('/home/sato/ahc074/runs')/(r+name)
 files=sorted(directory.glob('err/*.txt'))+sorted(directory.glob('orders/*/err/*.txt'))
 rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)} for f in files]
 results[name]={k:statistics.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('seed_finish_','value_seed_','joint_extra_')) or k in ['total_moves','req_sec','self_wrong','op_label_errors']}
(root/'metrics.json').write_text(json.dumps(results,indent=2)+'\n')
print('K2 diagnostics passed',flush=True)
