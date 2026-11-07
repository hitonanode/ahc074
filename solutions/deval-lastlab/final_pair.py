"""Task6's protocol: freeze priorities, select by final time, then replay one held-out solver."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,re,datetime,shutil
P=Path(__file__).resolve().parent;root=P.parents[1];runs=Path('/home/sato/ahc074/runs')
request_only_all='--request-only' in sys.argv[1:]
request_only_names={x.split('=',1)[1] for x in sys.argv[1:] if x.startswith('--request-only=')}
names=[x for x in sys.argv[1:] if not x.startswith('--request-only')];assert names
assert request_only_names <= set(names)
dirs={n:root/'solutions'/n for n in names};primary=dirs[names[0]]
digests={n:hashlib.sha256((p/'main.cpp').read_bytes()).hexdigest() for n,p in dirs.items()}
assert all((p/'main.cpp').stat().st_size<=522000 and not (p/'FROZEN.json').exists() for p in dirs.values())
for n,p in dirs.items():
    for f in ['builds.json','builds-native.json']:
        rows=json.loads((p/f).read_text());assert len(rows)==2 and all(z['returncode']==0 and z['source_sha256']==digests[n] for z in rows),(n,f)
    audit=json.loads((p/'source-audit.json').read_text());assert audit['sha256']==digests[n]
assert not any(k.startswith(('F3_','COLMDP_','DSEED_')) for k in os.environ)
assert os.environ.get('DEVAL_CXX','g++')=='g++' and os.environ.get('DEVAL_NATIVE','0')=='0'
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
for n,p in dirs.items():
    request_only=request_only_all or n in request_only_names
    freeze={'solution':n,'sha256':digests[n],'bytes':(p/'main.cpp').stat().st_size,'time':now,
            'selection_seeds':[0,500],'held_out_seeds':[500,2000] if request_only else [500,1000],'request_only':request_only,'priority':names,
            'rule':'Fixed priority from training; take the first solver with judge mean <=1.10*old and p99 <=nofb in the final same compare. Do not use scores to choose. Run held-out replay only for that one solver.'}
    (p/'FROZEN.json').write_text(json.dumps(freeze,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(log,args,n,orders):
    assert all(hashlib.sha256((p/'main.cpp').read_bytes()).hexdigest()==digests[name] for name,p in dirs.items())
    with log.open('w') as f:
        subprocess.run([sys.executable,str(P/'run.py')]+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',log.read_text(),re.M);assert ids
    for rid in ids:
        meta=json.loads((runs/rid/'meta.json').read_text());assert meta['status']=='ok'
        cases=json.loads((runs/rid/'result.json').read_text())['cases'];assert len(cases)==n
        assert all(len(c.get('order_scores',[c['score']]))==orders and min(c.get('order_scores',[c['score']]))>0 for c in cases)
    return ids
refs=['argon-des-perf-latew105','deval-vbranch-nofb','deval-flex125-plan3']
normal=run(primary/'final-normal.log',['--compare']+['solutions/'+x for x in refs+names]+
           ['--seeds','0-2000','--save-design','-c','Task6 frozen final priority '+','.join(names)],2000,1)
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'select_time.py'),names[0],*normal],cwd=root,env=env,check=True)
selection=json.loads((primary/'time-selection.json').read_text());chosen=selection['chosen']
if chosen is None:raise SystemExit('No frozen candidate meets the timing limits; held-out replay was not run.')
out=dirs[chosen]
request_only=json.loads((out/'FROZEN.json').read_text())['request_only']
if out!=primary:
    shutil.copy2(primary/'time-selection.json',out/'time-selection.json')
    shutil.copy2(primary/'final-normal.log',out/'final-normal.log')
design=next(r for r in normal if r.endswith('_'+chosen))
if request_only:
    replay_ids=run(out/'final-replay.log',['--compare','solutions/deval-flex125-plan3','solutions/'+chosen,
                  '--design-from','20261107-165305_deval-flex125-plan3','--orders','4','--seeds','0-2000',
                  '-c','Task6 frozen fixed-design request replay '+chosen],2000,4)
    replay=replay_ids[1]
    extra=['--request-reference',replay_ids[0]]
else:
    replay=run(out/'final-replay.log',['solutions/'+chosen,'--design-from',design,
               '--orders','8','--seeds','500-1000','-c','Task6 frozen held-out '+chosen],500,8)[0]
    extra=[]
(out/'final-runs.json').write_text(json.dumps({'normal':normal,'replay':replay,'request_only':request_only,'extra':extra},indent=2)+'\n')
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'final_metrics.py'),chosen,
                '--normal',*normal,'--replay',replay,*extra],cwd=root,env=env,check=True)
