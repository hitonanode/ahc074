from pathlib import Path
import subprocess,re
names=['argon-des-perf-condbound','argon-req-completevalue-v2','argon-req-completefast','argon-req-seed-eject-v2','argon-req-valueeject'];runs=['20261106-014450_'+x for x in names]
subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',*runs,'--json','solutions/argon-req-oldvalue/fast.json'],check=True)
root=Path('/home/sato/ahc074/runs')
for i,j in [(1,2),(3,4)]:
 a=root/runs[i];b=root/runs[j];fs=list((a/'out').glob('*.txt'))+list((a/'orders').glob('*/out/*.txt'))
 same=sum(f.read_bytes()==(b/f.relative_to(a)).read_bytes() for f in fs)
 labels=0
 for f in fs:
  rel=f.relative_to(a);rel=Path(*['err' if x=='out' else x for x in rel.parts])
  aa=[x for x in (a/rel).read_text().splitlines() if x.startswith(('@paper','@ops'))]
  bb=[x for x in (b/rel).read_text().splitlines() if x.startswith(('@paper','@ops'))]
  labels+=aa==bb
 print('EXACT',names[i],names[j],'stdout',same,'annotations',labels,'/',len(fs),flush=True)
 assert same==labels==len(fs)
