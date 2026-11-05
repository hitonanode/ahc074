from pathlib import Path
import subprocess
names=['argon-des-perf-condbound','argon-req-completevalue','argon-req-completevalue-v2','argon-req-jointk2-v2','argon-req-seed-eject-v2'];runs=['20261106-013732_'+x for x in names]
subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',*runs,'--json','solutions/argon-req-oldvalue/port.json'],check=True)
root=Path('/home/sato/ahc074/runs');a=root/runs[1];b=root/runs[2]
fs=list((a/'out').glob('*.txt'))+list((a/'orders').glob('*/out/*.txt'))
print('completed-value refactor identical stdout',sum(f.read_bytes()==(b/f.relative_to(a)).read_bytes() for f in fs),'/',len(fs))
