"""Verify all C++ features against Python, including final-state generic costs."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,subprocess
import numpy as np
HERE=Path(__file__).resolve().parent
d=np.load(HERE/'data/base.npz')
records=[]
for mode in ['static','fast','compact','filler','stationary','stationary32']:
    path=HERE/'data'/('base.'+mode+'.npz')
    if not path.exists():continue
    f=np.load(path);names=f['names'].tolist()
    for i in ([0,1,2,3,4,10,42,99] if mode!='filler' else [0,42]):
        out=subprocess.check_output([str(HERE/'bench_features'),str(d['paths'][i]),mode,'10'],text=True)
        values={line.split()[0]:float(line.split()[1]) for line in out.splitlines()}
        actual=np.array([values[k] for k in names])
        expected=f['X'][i]
        good=np.isclose(actual,expected,rtol=2.e-6,atol=2.e-5)
        assert good.all(),[(names[j],actual[j],expected[j]) for j in np.flatnonzero(~good)]
        r=dict(mode=mode,seed=int(d['seeds'][i]),milliseconds=values['__milliseconds'],init_milliseconds=values['__init_milliseconds'])
        records.append(r);print(r,flush=True)
(HERE/'feature_benchmark.json').write_text(json.dumps(records,indent=2))
