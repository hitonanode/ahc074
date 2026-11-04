from pathlib import Path
import subprocess,fcntl,signal,time,json
p=Path(__file__).resolve().parent;lock=open('/home/sato/ahc074/runs/.lock','rb')
for seed in (27,29,33):
 d=json.loads((p/'screen'/f'{seed:04}.json').read_text());data=(p.parent/'front-three'/f'{seed:04}.txt').read_text().splitlines();n=int(data[0].split()[0]);original=[int(row.split()[2])for row in data[1:n+1]];x=min((v for v in d['final']if v['opaque']!=original),key=lambda r:r['value']);mask=','.join(map(str,x['opaque']))
 out=(p/f'exact-{seed:04}.json').open('w');err=(p/f'exact-{seed:04}.err').open('w')
 proc=subprocess.Popen(['/tmp/ahc074-front-star-check',str(p.parent/'front-three'/f'{seed:04}.txt'),mask,'3000'],stdout=out,stderr=err);paused=False
 while proc.poll() is None:
  busy=False
  try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
  except BlockingIOError:busy=True
  if busy!=paused:proc.send_signal(signal.SIGSTOP if busy else signal.SIGCONT);paused=busy
  time.sleep(.5)
 out.close();err.close();print(seed,proc.returncode,(p/f'exact-{seed:04}.json').read_text(),flush=True)
