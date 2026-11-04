from pathlib import Path
import subprocess,fcntl,signal,time,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'scan';out.mkdir(exist_ok=True);lock=open('/home/sato/ahc074/runs/.lock','rb');waiting=list(range(24,40));active=[];paused=False;rows=[]
def busy():
 try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);return False
 except BlockingIOError:return True
while waiting or active:
 current=busy()
 if current!=paused:
  for seed,proc,files in active:
   if proc.poll()is None:proc.send_signal(signal.SIGSTOP if current else signal.SIGCONT)
  paused=current
 if not paused:
  while waiting and len(active)<2:
   seed=waiting.pop(0);files=[(out/f'{seed:04}.json').open('w'),(out/f'{seed:04}.err').open('w')]
   proc=subprocess.Popen(['/tmp/ahc074-cap-scan',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-205441_post-two/out/{seed:04}.txt'],stdout=files[0],stderr=files[1]);active.append((seed,proc,files))
 for item in active[:]:
  seed,proc,files=item
  if proc.poll()is not None:
   for f in files:f.close()
   if proc.returncode:raise RuntimeError((seed,proc.returncode))
   active.remove(item);row=json.loads((out/f'{seed:04}.json').read_text());rows.append(row);print(seed,row,flush=True)
 time.sleep(.5)
summary=dict(mean=statistics.mean(r['difference']for r in rows),se=statistics.stdev(r['difference']for r in rows)/math.sqrt(len(rows)),special=statistics.mean(r['special']for r in rows),novel=statistics.mean(r['novel']for r in rows),wins=sum(r['difference']<0 for r in rows),ties=sum(r['difference']==0 for r in rows),losses=sum(r['difference']>0 for r in rows))
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
