"""Repeat load-warned frozen replays and require byte-identical outputs.

The normal same-compare timing runs are not replaced by replay times.
"""
from pathlib import Path
import json,subprocess,sys,re,time

h=Path(__file__).resolve().parent;root=h.parents[1];r=Path('/home/sato/ahc074/runs')
def read(p):
    try:return json.loads(p.read_text())
    except (OSError,json.JSONDecodeError):return None
def warned(m):
    x=m.get('outside_load') or {}
    return x.get('mean_cores',0)>.5 or x.get('max_cores',0)>3
path=h/'clean-replay-checks.json'
out=read(path) or {'done':False,'checks':{}}
while True:
    rows=[]
    for k in [2,4,8]:rows.extend(read(h/f'heldout-b{k}-replay.json') or [])
    for row in rows:
        original=row['replay'];m=read(r/original/'meta.json')
        if not m or m.get('status')!='ok' or not warned(m) or original in out['checks']:continue
        tries=[]
        for attempt in range(1,4):
            tag=f'clean-repeat-{original}-{attempt}';log=h/(tag+'.log')
            cmd=[sys.executable,str(h/'run.py'),'solutions/deval-helper-wide',
                 '--design-from',row['source'],'--orders','8','--seeds','500-1000',
                 '-c',f'Task7 fixed replay repeat after load warning: {original}; attempt {attempt}']
            with log.open('w') as f:subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
            ids=re.findall(r'run-id: (\S+)',log.read_text());assert len(ids)==1
            repeated=ids[0];mm=read(r/repeated/'meta.json');assert mm['status']=='ok'
            artifact=h/(tag+'-identity.json')
            with (h/(tag+'-identity.log')).open('w') as f:
                subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',
                                sys.executable,str(h/'identity_orders.py'),original,repeated,
                                '--output',str(artifact)],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
            identity=read(artifact);assert identity['identical']==4000
            tries.append({'replay':repeated,'load':mm.get('outside_load'),'identity':identity})
            if not warned(mm):break
        assert not warned(mm),('No clean repetition after three attempts',original,tries)
        out['checks'][original]={'original_load':m.get('outside_load'),'clean_replay':repeated,'attempts':tries}
        path.write_text(json.dumps(out,indent=2)+'\n')
        print('Verified clean identical replay',original,'->',repeated,flush=True)
    records=read(h/'heldout-runs.json') or []
    # The last replay table and the aggregate manifest are separate writes.
    # If they changed during this iteration, rescan rather than fail on a race.
    if len(records)==3 and len(rows)==12:
        assert all(not warned(read(r/x['replay']/'meta.json')) or x['replay'] in out['checks'] for x in rows)
        out['done']=True;path.write_text(json.dumps(out,indent=2)+'\n');break
    time.sleep(10)
print('All frozen replay load warnings checked.',flush=True)
