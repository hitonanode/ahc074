from pathlib import Path
import subprocess,sys,json,re,statistics as st,hashlib
base,cand=sys.argv[1:];p=Path('solutions/argon-req-completefast-v3');fixed='20261106-021624_argon-req-completefast-v3';root=Path('/home/sato/ahc074/runs')
assert p.joinpath('main.cpp').read_bytes()==(root/cand/'src/main.cpp').read_bytes()==(root/fixed/'src/main.cpp').read_bytes()
with p.joinpath('normal-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',base,cand,'--json',str(p/'normal-results.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
with p.joinpath('validation.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/check_final.py',base,cand,fixed,str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
with p.joinpath('judge-model.log').open('w') as f:
 subprocess.run(['/home/sato/ahc074/.venv/bin/python','/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/argon/judge_model.py',base,cand],stdout=f,stderr=subprocess.STDOUT,check=True)
rows=[]
for f in (root/cand/'err').glob('*.txt'):
 rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)})
metrics={k:st.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('complete_value','value_filler'))}
p.joinpath('local-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print('All PR139 final artifact checks passed.',flush=True)
