"""Final generated C++ V equals the frozen Python model. Training seeds only."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,subprocess
import numpy as np
HERE=Path(__file__).resolve().parent
f=json.loads((HERE/'FROZEN.json').read_text());name=f['selected_model']
p=np.load(HERE/'models/final_predictions.npz')
tags=p['variants'].tolist();records=[]
for compiler in ['g++','clang++']:
    binary=HERE/('bench_value_gcc' if compiler=='g++' else 'bench_value_clang')
    for tag,seed in [('base',0),('base',1),('base',42),('base',99),
                     ('DESIGN_SEED_1',3),('DESIGN_SEED_3',399),('DSEED_A_1',10),('DSEED_A_3',499)]:
        d=np.load(HERE/'data'/(tag+'.npz'))
        row=int(np.flatnonzero(d['seeds']==seed)[0])
        out=subprocess.check_output([str(binary),str(d['paths'][row]),'30'],text=True)
        actual,ms,init,checksum=map(float,out.split())
        expected=float(p[name][seed,tags.index(tag)])
        assert abs(actual-expected)<2.e-5,(tag,seed,actual,expected)
        records.append(dict(compiler=compiler,variant=tag,seed=seed,prediction=actual,
                            python_prediction=expected,error=actual-expected,
                            milliseconds=ms,init_milliseconds=init))
        print(compiler,tag,seed,'difference',actual-expected,'milliseconds',ms,flush=True)
(HERE/'value_benchmark.json').write_text(json.dumps(records,indent=2))
