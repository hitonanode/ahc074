from pathlib import Path
import subprocess,fcntl,signal,time,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'models';out.mkdir(exist_ok=True);lock=open('/home/sato/ahc074/runs/.lock','rb');waiting=[(seed,a,b)for seed in range(24,32)for a,b in [(0,12),(0,24),(8,24),(16,24)]];active=[];paused=False;rows=[]
def busy():
 try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);return False
 except BlockingIOError:return True
while waiting or active:
 current=busy()
 if current!=paused:
  for key,proc,files in active:
   if proc.poll()is None:proc.send_signal(signal.SIGSTOP if current else signal.SIGCONT)
  paused=current
 if not paused:
  while waiting and len(active)<2:
   seed,a,b=waiting.pop(0);key=f'{seed:04}-{a}-{b}';profile=out/f'{key}.txt'
   result=subprocess.run(['python3',str(p/'profile.py'),str(seed),f'{a},{b}'],text=True,capture_output=True,check=True);profile.write_text(result.stdout)
   files=[(out/f'{key}.json').open('w'),(out/f'{key}.err').open('w')]
   proc=subprocess.Popen(['/tmp/ahc074-overhang-lab',str(profile),'16384','131072'],stdout=files[0],stderr=files[1]);active.append((key,proc,files))
 for item in active[:]:
  key,proc,files=item
  if proc.poll()is not None:
   for f in files:f.close()
   if proc.returncode:raise RuntimeError((key,proc.returncode))
   active.remove(item);row=json.loads((out/f'{key}.json').read_text());rows.append(dict(key=key,**row));print(key,row,flush=True)
 time.sleep(.5)
(out/'summary.json').write_text(json.dumps(rows,indent=2))
