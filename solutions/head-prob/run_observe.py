from pathlib import Path
import subprocess,fcntl,signal,time,json
p=Path(__file__).resolve().parent;out=p/'observed';out.mkdir(exist_ok=True);lock=open('/home/sato/ahc074/runs/.lock','rb')
for seed in range(24,40):
 while True:
  try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);break
  except BlockingIOError:time.sleep(.5)
 f=(out/f'{seed:04}.json').open('w');e=(out/f'{seed:04}.err').open('w')
 proc=subprocess.Popen(['/tmp/ahc074-head-prob-observe',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-194429_anchor-match/out/{seed:04}.txt'],stdout=f,stderr=e);paused=False
 while proc.poll()is None:
  busy=False
  try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
  except BlockingIOError:busy=True
  if busy!=paused:proc.send_signal(signal.SIGSTOP if busy else signal.SIGCONT);paused=busy
  time.sleep(.5)
 f.close();e.close()
 if proc.returncode:raise RuntimeError((seed,proc.returncode))
 print(seed,flush=True)
