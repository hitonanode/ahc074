"""Fixed-iteration design study; does not run future requests or claim contest scores."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess

D=Path(__file__).resolve().parent
out=D/'models';out.mkdir(exist_ok=True)
jobs=[(g,seed) for g in (34,36,38,40,42,44) for seed in range(24,32)]
env=os.environ | {'MODEL_ONLY':'1','MAP_ITERS':'100000','GOPT_STEPS':'20000',
                  'ANNEAL_ITERS':'20000000','CLIMB_ITERS':'60000'}
(out/'meta.json').write_text(json.dumps({'seeds':[24,32],'generic_windows':[34,36,38,40,42,44],
    'fixed':{k:env[k] for k in ['MODEL_ONLY','MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS']}},indent=2)+'\n')
def job(item):
    g,seed=item;name=f'g{g}-{seed:04d}';path=out/f'{name}.json'
    if path.exists():return json.loads(path.read_text())
    with open(f'/home/sato/ahc074/tools/in/{seed:04d}.txt','rb') as inp:
        result=subprocess.run(['/tmp/ahc074-eight'],stdin=inp,capture_output=True,
                              env=env|{'EIGHT_G':str(g)},timeout=180)
    log=result.stderr.decode();(out/f'{name}.err').write_text(log)
    stats={key:float(value) for key,value in re.findall(r'(?m)^(\w+) = ([-+0-9.eE]+)$',log)}
    record={'g':g,'seed':seed,'exit_code':result.returncode,'stats':stats}
    path.write_text(json.dumps(record,indent=2)+'\n')
    print(name,result.returncode,stats.get('model_cost'),stats.get('gobj_after'),flush=True)
    return record
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(job,jobs))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
