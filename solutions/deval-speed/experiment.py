"""Sequential recorded design/replay experiments. Compile and analysis use flock."""
from pathlib import Path
import subprocess, os, sys, re, json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PY='/home/sato/ahc074/.venv/bin/python'
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
def run(tag,solution,settings,seeds='0-500'):
    existing=settings.pop('DESIGN_FROM',None)
    results=[existing] if existing else []
    for phase in (['replay'] if existing else ['design','replay']):
        args=[PY,str(HERE/'run.py'),solution,'--seeds',seeds,'--no-record','-c',f'deval Task3 {tag} {phase}: {settings}']
        if phase=='design': args+=['--save-design']
        else: args+=['--design-from',results[0],'--orders','8']
        log=HERE/f'{tag}.{phase}.log'
        with log.open('w') as f: subprocess.run(args,env=ENV|settings,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        text=log.read_text()
        results.append(re.search(r'run-id: (\S+)',text)[1])
        print(tag,phase,results[-1],flush=True)
    row={'tag':tag,'solution':solution,'settings':settings,'seeds':seeds,'design':results[0],'replay':results[1]}
    with (HERE/'experiments.jsonl').open('a') as f: f.write(json.dumps(row)+'\n')
    return row
if __name__=='__main__':
    tag=sys.argv[1]
    settings=dict(x.split('=',1) for x in sys.argv[2:])
    seeds=settings.pop('SEEDS','0-500')
    solution=settings.pop('SOLUTION','solutions/deval-vbranch-o3')
    run(tag,solution,settings,seeds)
