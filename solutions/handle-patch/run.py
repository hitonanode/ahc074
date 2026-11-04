from pathlib import Path
import subprocess,fcntl,signal,time,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'models';out.mkdir(exist_ok=True);lock=open('/home/sato/ahc074/runs/.lock','rb');rows=[]
for seed in range(24,56):
 while True:
  try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);break
  except BlockingIOError:time.sleep(.5)
 f=(out/f'{seed:04}.json').open('w');e=(out/f'{seed:04}.err').open('w');proc=subprocess.Popen(['/tmp/ahc074-handle-patch',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-202421_reset-head/out/{seed:04}.txt'],stdout=f,stderr=e);paused=False
 while proc.poll()is None:
  busy=False
  try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
  except BlockingIOError:busy=True
  if busy!=paused:proc.send_signal(signal.SIGSTOP if busy else signal.SIGCONT);paused=busy
  time.sleep(.2)
 f.close();e.close()
 if proc.returncode:raise RuntimeError((seed,proc.returncode))
 row=json.loads((out/f'{seed:04}.json').read_text());rows.append(row);print(seed,[(v['charge'],v['difference'],v['selected'])for v in row['conditions']],flush=True)
summary={}
for i,charge in enumerate([1,1.6,2]):
 x=[r['conditions'][i]for r in rows];v=[r['difference']for r in x];summary[charge]=dict(mean=statistics.mean(v),se=statistics.stdev(v)/math.sqrt(len(v)),selected=statistics.mean(r['selected']for r in x))
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
