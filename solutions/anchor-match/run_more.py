from pathlib import Path
import subprocess,json,time,fcntl,signal,statistics,math
p=Path(__file__).resolve().parent;lock=open('/home/sato/ahc074/runs/.lock','rb')
def busy():
 try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);return False
 except BlockingIOError:return True
while busy():time.sleep(.5)
configs=[('relax',p/'probe_relax.cpp','mode',[1,2,3]),('joint',p/'probe_joint.cpp','mode',[1,2,3,4]),('start',p.parent/'priority-start/probe.cpp','mode',[1,2,3])]
for name,src,key,modes in configs:
 subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(src),'-o',f'/tmp/ahc074-anchor-{name}'],check=True)
 out=p/name;out.mkdir(exist_ok=True);waiting=list(range(24,56));active=[];paused=False;rows=[]
 while waiting or active:
  current=busy()
  if current!=paused:
   for seed,proc,files in active:
    if proc.poll() is None:proc.send_signal(signal.SIGSTOP if current else signal.SIGCONT)
   paused=current
  if not paused:
   while waiting and len(active)<2:
    seed=waiting.pop(0);files=[(out/f'{seed:04}.json').open('w'),(out/f'{seed:04}.err').open('w')]
    proc=subprocess.Popen([f'/tmp/ahc074-anchor-{name}',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','16','8'],stdout=files[0],stderr=files[1]);active.append((seed,proc,files))
  for item in active[:]:
   seed,proc,files=item
   if proc.poll() is not None:
    for f in files:f.close()
    if proc.returncode:raise RuntimeError((name,seed,proc.returncode))
    active.remove(item);d=json.loads((out/f'{seed:04}.json').read_text());rows.append(d);print(name,seed,[(r[key],r['difference'])for r in d],flush=True)
  time.sleep(.5)
 summary={}
 for mode in modes:
  x=[next(r for r in row if r[key]==mode)['difference']for row in rows];summary[mode]=dict(mean=statistics.mean(x),se=statistics.stdev(x)/math.sqrt(len(x)),wins=sum(v<0 for v in x),ties=sum(v==0 for v in x),losses=sum(v>0 for v in x))
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(name,summary,flush=True)
