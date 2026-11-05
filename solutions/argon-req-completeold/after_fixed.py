from pathlib import Path
import subprocess, sys, re, json
p=Path(__file__).resolve().parent
for log in ['smoke.log','full-smoke.log','eject-fixed.log']:
 subprocess.run([sys.executable,str(p/'analyze_screen.py'),str(p/log)],check=True)
root=Path('/home/sato/ahc074/runs')
def compare(a,b):
 aa=root/a;bb=root/b
 files=list((aa/'out').glob('*.txt'))+list((aa/'orders').glob('*/out/*.txt'))
 for f in files:
  rel=f.relative_to(aa)
  assert f.read_bytes()==(bb/rel).read_bytes(),rel
  ef=Path(str(rel).replace('out/','err/'))
  def lines(path):
   return [x for x in path.read_text().splitlines() if not re.match(r'^\w+_sec = ',x) and not x.startswith(('Score = ', '#'))]
  if 'jointfinish' in b: assert lines(aa/ef)==lines(bb/ef),ef
 print('Identical stdout',a,b,len(files),flush=True)
compare('20261106-025900_argon-req-completefast-v3','20261106-025900_argon-req-jointfinish')
compare('20261106-024741_argon-req-completeeject','20261106-025309_argon-req-completeeject-profile')
print('Analysis and saved-output checks passed.',flush=True)
