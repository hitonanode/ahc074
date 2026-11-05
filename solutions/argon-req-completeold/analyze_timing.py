from pathlib import Path
import subprocess,sys,re
w=Path(__file__).resolve().parent
for f in ['solutions/argon-req-ejectcache/time-probe.log','solutions/argon-req-ejecthelper/normal-screen.log']:
 with Path(f).with_name(Path(f).stem+'-analysis.log').open('w') as out:
  subprocess.run([sys.executable,str(w/'analyze_screen.py'),f],stdout=out,stderr=subprocess.STDOUT,check=True)
p=Path('solutions/argon-req-ejecthelper');names=re.findall(r'run-id: (\S+)',(p/'normal-screen.log').read_text());assert len(names)==3
r=Path('/home/sato/ahc074/runs');a=r/names[1];b=r/names[2]
files=list((a/'out').glob('*.txt'));assert len(files)==200
for f in files:
 assert f.read_bytes()==(b/'out'/f.name).read_bytes(),f
 def cleaned(x):return [line for line in x.read_text().splitlines() if not re.match(r'^\w+_sec = ',line)]
 assert cleaned(a/'err'/f.name)==cleaned(b/'err'/f.name),f
print('Helper extraction: all 200 stdout and non-timing stderr identical.',flush=True)
with Path('solutions/argon-req-ejectcache/trace-validation.log').open('w') as out:
 subprocess.run([sys.executable,str(w/'check_trace.py')],stdout=out,stderr=subprocess.STDOUT,check=True)
print('Correct heavy-trace switch and output paths verified.',flush=True)
