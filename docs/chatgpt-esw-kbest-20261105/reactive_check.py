#!/usr/bin/env python3
"""Only release a request after receiving the preceding complete response."""
import argparse, json, os, selectors, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('solver',type=Path);p.add_argument('input',type=Path)
p.add_argument('--judge',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--fixed-work',action='store_true');p.add_argument('--timeout',type=float,default=60)
p.add_argument('--env',action='append',default=[]);a=p.parse_args()
text=a.input.read_text().splitlines();n,k,P,R=map(int,text[0].split());queries=text[1+P:];assert len(queries)==R
initial='\n'.join(text[:1+P])+'\n';env=os.environ.copy()
if a.fixed_work:env.update(FIXED_WORK='1',MAP_ITERS='262144',GOPT_STEPS='65536',ANNEAL_ITERS='12582912',CLIMB_ITERS='32768',NO_FALLBACK='1')
for x in a.env:key,value=x.split('=',1);env[key]=value
a.output.parent.mkdir(parents=True,exist_ok=True);buffer=b'';output=[];start=time.perf_counter()
with a.output.with_suffix('.err').open('wb') as err:
    proc=subprocess.Popen([str(a.solver.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0,env=env)
    sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
    def line():
        global buffer
        while b'\n' not in buffer:
            remaining=a.timeout-(time.perf_counter()-start)
            if remaining<=0 or not sel.select(remaining):raise TimeoutError('reactive response timed out')
            data=os.read(proc.stdout.fileno(),65536)
            if not data:raise RuntimeError('premature EOF')
            buffer+=data
        result,buffer=buffer.split(b'\n',1);output.append(result+b'\n');return result.decode()
    try:
        proc.stdin.write(initial.encode());proc.stdin.flush()
        for _ in range(k):
            s=line();assert len(s)==n and set(s)<=set('01.')
        for u in queries:
            proc.stdin.write((u+'\n').encode());proc.stdin.flush();moves=int(line());assert 0<=moves<=2*k
            for _ in range(moves):assert len(line().split())==2
        proc.stdin.close();proc.wait(timeout=max(.1,a.timeout-(time.perf_counter()-start)))
        assert not buffer.strip() and not proc.stdout.read().strip() and proc.returncode==0
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        sel.close()
wall=time.perf_counter()-start;a.output.write_bytes(b''.join(output))
result=json.loads(subprocess.check_output([str(a.judge.resolve()),str(a.input),str(a.output)]))
assert result.get('valid') and result['errors']==0,result
result.update(wall_sec=wall,solver=a.solver.name,input=a.input.name)
a.output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
