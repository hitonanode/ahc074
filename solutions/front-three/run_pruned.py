from pathlib import Path
import subprocess,time,signal,fcntl,json
folder=Path(__file__).resolve().parent
waiting=[27,29,30,33];active=[];paused=False
lock=open('/home/sato/ahc074/runs/.lock','rb')
while waiting or active:
    if (folder/'stop-pruned').exists():
        for seed,p,files in active:
            p.send_signal(signal.SIGCONT);p.terminate()
        for seed,p,files in active:
            p.wait()
            for f in files:f.close()
        print('stopped',flush=True);break
    busy=False
    try:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        fcntl.flock(lock,fcntl.LOCK_UN)
    except BlockingIOError:busy=True
    if busy!=paused:
        for seed,p,files in active:
            if p.poll() is None:p.send_signal(signal.SIGSTOP if busy else signal.SIGCONT)
        paused=busy;print('paused for official evaluation' if busy else 'resumed',flush=True)
    if not paused:
        while waiting and len(active)<2:
            seed=waiting.pop(0)
            files=[(folder/f'pruned-{seed:04}.json').open('w'),(folder/f'pruned-{seed:04}.err').open('w')]
            p=subprocess.Popen(['/tmp/ahc074-front-three-pruned',str(folder/f'{seed:04}.txt'),'2','1'],stdout=files[0],stderr=files[1])
            active.append((seed,p,files));print('started',seed,flush=True)
    for job in active[:]:
        seed,p,files=job
        if p.poll() is not None:
            for f in files:f.close()
            active.remove(job)
            print('finished',seed,p.returncode,flush=True)
            if p.returncode==0:print(json.loads((folder/f'pruned-{seed:04}.json').read_text()),flush=True)
    time.sleep(.5)
