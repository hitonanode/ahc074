from pathlib import Path
import subprocess,sys,re
w=Path(__file__).resolve().parent;log=w/'layout-screen.log'
subprocess.run([sys.executable,str(w/'analyze_screen.py'),str(log)],check=True)
names=re.findall(r'run-id: (\S+)',log.read_text());assert len(names)==4
root=Path('/home/sato/ahc074/runs');base=root/names[1]
for name in names[2:]:
 r=root/name
 files=list((base/'out').glob('*.txt'));assert len(files)==200
 for f in files:
  assert f.read_bytes()==(r/'out'/f.name).read_bytes(),(name,f.name)
  def clean(path):return [x for x in path.read_text().splitlines() if not re.match(r'^\w+_sec = ',x)]
  assert clean(base/'err'/f.name)==clean(r/'err'/f.name),(name,f.name)
 print(name,'200 stdout and all non-timing stderr identical to ejecthelper.',flush=True)
