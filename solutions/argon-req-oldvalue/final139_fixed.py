from pathlib import Path
import subprocess,json
p=Path('solutions/argon-req-completefast-v3');base='20261106-021624_argon-des-perf-gaincache';cand='20261106-021624_argon-req-completefast-v3'
assert len(json.loads(Path('/home/sato/ahc074/runs',cand,'result.json').read_text())['cases'])==2000
for suffix,end in [('screen',200),('fixed',2000)]:
 with p.joinpath(suffix+'-analysis.log').open('w') as f:
  subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',base,cand,'--end',str(end),'--json',str(p/(suffix+'-results.json'))],stdout=f,stderr=subprocess.STDOUT,check=True)
with p.joinpath('builds.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/check_builds.py',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
print('PR139 fixed comparison and all four builds complete.',flush=True)
