"""Task4's protocol: freeze priorities, select by final time, then replay one held-out solver."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,re,datetime,shutil
P=Path(__file__).resolve().parent;root=P.parents[1];runs=Path('/home/sato/ahc074/runs')
names=sys.argv[1:];assert names
dirs={n:root/'solutions'/n for n in names};primary=dirs[names[0]]
digests={n:hashlib.sha256((p/'main.cpp').read_bytes()).hexdigest() for n,p in dirs.items()}
assert all((p/'main.cpp').stat().st_size<=522000 and not (p/'FROZEN.json').exists() for p in dirs.values())
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
for n,p in dirs.items():
    freeze={'solution':n,'sha256':digests[n],'bytes':(p/'main.cpp').stat().st_size,'time':now,
            'selection_seeds':[0,500],'held_out_seeds':[500,1000],'priority':names,
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
refs=['argon-des-perf-latew105','deval-vbranch-nofb','deval-ordered8']
normal=run(primary/'final-normal.log',['--compare']+['solutions/'+x for x in refs+names]+
           ['--seeds','0-2000','--save-design','-c','Task5 frozen final priority '+','.join(names)],2000,1)
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'select_time.py'),names[0],*normal],cwd=root,env=env,check=True)
selection=json.loads((primary/'time-selection.json').read_text());chosen=selection['chosen']
if chosen is None:raise SystemExit('No frozen candidate meets the timing limits; held-out replay was not run.')
out=dirs[chosen]
if out!=primary:
    shutil.copy2(primary/'time-selection.json',out/'time-selection.json')
    shutil.copy2(primary/'final-normal.log',out/'final-normal.log')
design=next(r for r in normal if r.endswith('_'+chosen))
replay=run(out/'final-replay.log',['solutions/'+chosen,'--design-from',design,
           '--orders','8','--seeds','500-1000','-c','Task5 frozen held-out '+chosen],500,8)[0]
(out/'final-runs.json').write_text(json.dumps({'normal':normal,'replay':replay},indent=2)+'\n')
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'final_metrics.py'),chosen,
                '--normal',*normal,'--replay',replay],cwd=root,env=env,check=True)
