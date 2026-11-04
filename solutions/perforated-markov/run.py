from pathlib import Path
import subprocess,fcntl,signal,time,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'models';out.mkdir(exist_ok=True);lock=open('/home/sato/ahc074/runs/.lock','rb');waiting=list(range(120,152));active=[];paused=False;rows=[]
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
   proc=subprocess.Popen(['/tmp/ahc074-perforated-markov',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-230624_post-repair/out/{seed:04}.txt','16'],stdout=files[0],stderr=files[1]);active.append((seed,proc,files))
 for item in active[:]:
  seed,proc,files=item
  if proc.poll()is not None:
   for f in files:f.close()
   if proc.returncode:raise RuntimeError((seed,proc.returncode))
   active.remove(item);row=json.loads((out/f'{seed:04}.json').read_text());rows.append(row);print(seed,[(r['mode'],r['difference'],r['seconds'])for r in row],flush=True)
 time.sleep(.5)
summary={}
for mode in range(1,6):
 x=[r[mode]for r in rows];v=[r['difference']for r in x];summary[mode]=dict(mean=statistics.mean(v),se=statistics.stdev(v)/math.sqrt(len(v)),wins=sum(t<0 for t in v),ties=sum(t==0 for t in v),losses=sum(t>0 for t in v),seconds=statistics.mean(r['seconds']for r in x),holes=statistics.mean(r['holes']for r in x),model=statistics.mean(r['model']for r in x))
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
