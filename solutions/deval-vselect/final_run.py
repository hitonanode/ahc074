"""Run the frozen final protocol, with no parameter selection on test scores."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PY='/home/sato/ahc074/.venv/bin/python'
ENV={k:v for k,v in os.environ.items() if not k.startswith(('DEVAL_','DSEED_')) and
     k not in {'DESIGN_SEED','MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','AS_WORK','AS_ELITE'}}
ENV.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
LOCK='/home/sato/ahc074/runs/.lock'
def run(args,path,env=ENV):
    with path.open('w') as out:subprocess.run(args,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
    return re.findall(r'run-id: (\S+)',path.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('solution');a=p.parse_args()
    dest=ROOT/a.solution
    frozen=json.loads((dest/'FROZEN.json').read_text())
    assert hashlib.sha256((dest/'main.cpp').read_bytes()).hexdigest()==frozen['source_sha256']
    runner=[PY,str(HERE/'run.py')]
    ref,candidate=run(runner+['--compare','solutions/argon-des-perf-latew105',a.solution,
        '--seeds','0-2000','--save-design','--no-record','-c','deval Task2 frozen final 2000 compare'],dest/'final-compare.log')
    print('normal',ref,candidate,flush=True)
    [replay]=run(runner+[a.solution,'--design-from',candidate,'--orders','8','--seeds','0-1000',
        '--no-record','-c','deval Task2 frozen final 8-list replay'],dest/'final-replay.log')
    print('replay',replay,flush=True)
    [guard]=run(runner+[a.solution,'--seeds','0-500','--no-record','-c','deval Task2 final guard stress clock x2'],
        dest/'final-guard.log',ENV|{'DEVAL_GUARD_STRESS':'2'})
    print('guard',guard,flush=True)
    run(['flock','-x',LOCK,'clang++','-std=c++23','-O2','-DCLOCK_SCALE=1.1','-DLOCAL_BENCH',
         str(dest/'main.cpp'),'-o',str(dest/'clang-check')],dest/'clang-check.log')
    run(['flock','-x',LOCK,PY,str(HERE/'analyze.py')],HERE/'analysis.log')
    run(['flock','-x',LOCK,PY,str(HERE/'summarize_final.py'),'--reference',ref,'--candidate',candidate,
         '--replay',replay,'--solution',a.solution,'--guard',guard],dest/'final-summary.log')
    if (dest/'audit.py').exists():
        run(['flock','-x',LOCK,PY,str(dest/'audit.py')],dest/'audit.log')
    run([PY,str(HERE/'write_report.py'),a.solution],dest/'write-report.log')
    print('complete',a.solution,flush=True)
if __name__=='__main__':main()
