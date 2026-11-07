"""Freeze a training-selected solver, then run the prescribed recorded final checks."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,re,datetime
P=Path(__file__).resolve().parent;root=P.parents[1];runs=Path('/home/sato/ahc074/runs')
name=sys.argv[1];out=root/'solutions'/name;source=out/'main.cpp'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert len(source.read_bytes())<=522000
freeze={'solution':name,'sha256':digest,'bytes':source.stat().st_size,
        'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        'selection_seeds':[0,500],'held_out_seeds':[500,1000],
        'rule':'Source and settings selected on training seeds only; no quality tuning after this freeze.'}
assert not (out/'FROZEN.json').exists()
(out/'FROZEN.json').write_text(json.dumps(freeze,indent=2)+'\n')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(log,args,n,orders):
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    with (out/log).open('w') as f:
        subprocess.run([sys.executable,str(P/'run.py')]+args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',(out/log).read_text(),re.M)
    assert ids
    for rid in ids:
        meta=json.loads((runs/rid/'meta.json').read_text());assert meta['status']=='ok'
        cases=json.loads((runs/rid/'result.json').read_text())['cases'];assert len(cases)==n
        assert all(len(c.get('order_scores',[c['score']]))==orders and min(c.get('order_scores',[c['score']]))>0 for c in cases)
    return ids
refs=['argon-des-perf-latew105','deval-vbranch-nofb','deval-ordered8']
normal=run('final-normal.log',['--compare']+['solutions/'+x for x in refs+[name]]+
           ['--seeds','0-2000','--save-design','-c','Task5 frozen final '+name],2000,1)
replay=run('final-replay.log',['solutions/'+name,'--design-from',normal[-1],
           '--orders','8','--seeds','500-1000','-c','Task5 frozen held-out '+name],500,8)[0]
(out/'final-runs.json').write_text(json.dumps({'normal':normal,'replay':replay},indent=2)+'\n')
subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'final_metrics.py'),name,
                '--normal',*normal,'--replay',replay],cwd=root,env=env,check=True)
