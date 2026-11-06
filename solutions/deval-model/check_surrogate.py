"""Export fixed quadrature points, verify C++/Numba equality, time C++.

The C++ binary must already be built. Run the entire operation under flock.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,subprocess
import numpy as np
from features import static_features,poset_table,donor_tables,cover_expectation,qmc_samples

HERE=Path(__file__).resolve().parent
d=np.load(HERE/'data/base.npz')
states=json.loads((HERE/'data/base.states.json').read_text())
table=poset_table()
records=[]
for i in [0,1,2,3,4,10,42,99]:
    st=states[i]
    _,_,aux=static_features(st,table)
    hb,op,bl,col,ded,H,nc,nt,n1,p1,xy,freq=aux
    x,y=xy.T;prob=(y+2*nt*(y>x))/np.maximum(1,x+y+2*nt)
    samples=qmc_samples(H)
    sp=HERE/f'samples-{H}.bin';samples.tofile(sp)
    covers,starts,utility,heads=donor_tables(hb,op,bl,col,ded,H,prob,freq)
    T,_=cover_expectation(hb,op,bl,col,ded,H,prob,covers,starts,heads,samples,1.6)
    out=subprocess.check_output([str(HERE/'bench_surrogate'),str(d['paths'][i]),str(sp),'20'],text=True)
    values={line.split()[0]:list(map(float,line.split()[1:])) for line in out.splitlines()}
    expected=np.mean(T,axis=0)
    assert np.allclose(values['mean'],expected,rtol=0,atol=1.e-11),(i,values,expected)
    hv=sum(utility[heads[c,0]]*(1-prob[c])+utility[heads[c,1]]*prob[c] for c in range(H))/256
    assert abs(hv-values['headutility'][0])<1.e-11
    records.append(dict(seed=int(d['seeds'][i]),milliseconds=values['milliseconds'][0]))
    print('seed',i,'C++ == Numba; ms',values['milliseconds'][0],flush=True)
(HERE/'benchmark.json').write_text(json.dumps(records,indent=2))
