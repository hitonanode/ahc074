from pathlib import Path
import subprocess,fcntl,signal,time,json
p=Path(__file__).resolve().parent
lock=open('/home/sato/ahc074/runs/.lock','rb')
for seed in (29,27,30,33):
    while True:
        try:
            d=json.loads((p/f'{seed:04}.json').read_text())
            break
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.5)
    chains=sorted((x for x in d['final'] if x['chain']),key=lambda x:x['value'])
    others=sorted((x for x in d['final'] if not x['chain']),key=lambda x:x['value'])
    chosen=[chains[0]]+others
    candidates=p/f'candidates-{seed:04}.txt'
    candidates.write_text('\n'.join(','.join(map(str,x['opaque'])) for x in chosen)+'\n')
    while True:
        try:
            fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            fcntl.flock(lock,fcntl.LOCK_UN)
            break
        except BlockingIOError:time.sleep(.5)
    out=(p/f'exact-{seed:04}.json').open('w');err=(p/f'exact-{seed:04}.err').open('w')
    proc=subprocess.Popen(['/tmp/ahc074-front-network-check',str(p.parent/'front-three'/f'{seed:04}.txt'),str(candidates),'3000'],stdout=out,stderr=err)
    paused=False
    while proc.poll() is None:
        busy=False
        try:
            fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            fcntl.flock(lock,fcntl.LOCK_UN)
        except BlockingIOError:busy=True
        if busy!=paused:
            proc.send_signal(signal.SIGSTOP if busy else signal.SIGCONT);paused=busy
        time.sleep(.5)
    out.close();err.close()
    print(seed,proc.returncode,(p/f'exact-{seed:04}.json').read_text(),flush=True)
