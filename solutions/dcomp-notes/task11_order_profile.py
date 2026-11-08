from pathlib import Path
import json,collections,numpy as np
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent
T=json.loads((N/'t11-tail.json').read_text());result={}
for cc,rid in [('gcc','20261108-162439_dcomp-t11-profile'),('clang','20261108-162556_dcomp-t11-profile')]:
 slow=set(T[cc]['slow25']); reqslow=set(T[cc]['req25'])
 lens=collections.defaultdict(lambda:np.zeros(5));ops=collections.defaultdict(lambda:np.zeros(6));perorder=np.zeros((500,1024,3));excs=collections.defaultdict(lambda:np.zeros(3))
 for seed in range(500):
  with (R/rid/'err'/f'{seed:04d}.txt').open() as f:
   for line in f:
    if line.startswith('#f3post '):
     z=line.split();r,stage,m=int(z[1]),int(z[2]),int(z[4]);sec=float(z[9]);gain=float(z[7]);saved=m-int(z[8]);
     lens[m]+=np.array([1,sec,gain,saved,float(seed in reqslow)*sec]);perorder[seed,r,0]+=sec
    elif line.startswith('#f3op '):
     z=line.split();r,op=int(z[1]),int(z[7]);n,ok,accept=int(z[8]),int(z[9]),int(z[10]);sec=float(z[13]);saved=float(z[12]);
     ops[op]+=np.array([1,n,ok,accept,sec,saved]);perorder[seed,r,1]+=n;perorder[seed,r,2]+=ok
    elif line.startswith('cfprof_') and '_exc = ' in line:
     k,_,v=line.split();q=float(v);excs[k]+=np.array([q,q*(seed in slow),q*(seed in reqslow)])
 v={'run':rid,'by_input_length':{str(k):a.tolist() for k,a in sorted(lens.items())},'by_operator':{str(k):a.tolist() for k,a in sorted(ops.items())},'exclusive':{k:(a/np.array([500,25,25])).tolist() for k,a in excs.items()},'perorder_quantiles':{str(p):np.percentile(perorder.reshape(-1,3),p,axis=0).tolist() for p in [50,90,95,99,99.5,99.9,100]}}
 result[cc]=v;print(cc,json.dumps(v,ensure_ascii=False))
(N/'t11-order-profile.json').write_text(json.dumps(result,indent=2)+'\n')
