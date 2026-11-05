from pathlib import Path
import subprocess
r='20261106-055840_'
names=['argon-req-ejectstats-v2','argon-req-newfull-only','argon-req-newfull-fast','argon-req-newfull-probe']
p=Path('solutions/argon-req-newfull-only')
with (p/'screen-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-completeold/analyze.py',*[r+n for n in names],'--end','200','--json',str(p/'screen-results.json')],stdout=f,check=True)
with (p/'oracle-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-oldfull-v2/analyze_oracles.py',r+names[0],r+names[-1],'--json',str(p/'oracle-results.json')],stdout=f,check=True)
with (p/'exact.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-exactprofile/check_exact.py',r+names[1],r+names[2]],stdout=f,check=True)
print('Newfull analysis passed',flush=True)
