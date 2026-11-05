import subprocess
runs=['20261106-015127_'+s for s in ['argon-des-perf-condbound','argon-req-completefast','argon-req-jointk2-v2','argon-req-valueeject']]
with open('solutions/argon-req-oldvalue/fixed-analysis.log','w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',*runs,'--json','solutions/argon-req-oldvalue/fixed.json'],stdout=f,stderr=subprocess.STDOUT,check=True)
with open('solutions/argon-req-oldvalue/completefast-episodes.log','w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/episodes.py',runs[0],runs[1]],stdout=f,stderr=subprocess.STDOUT,check=True)
with open('solutions/argon-req-completefast/builds.log','w') as f:
 subprocess.run(['python3','solutions/argon-req-oldvalue/check_builds.py','solutions/argon-req-completefast'],stdout=f,stderr=subprocess.STDOUT,check=True)
print('Fixed analysis, saved-output observations and four builds complete.',flush=True)
