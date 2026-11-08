"""Paired replay results clustered by seed, with new order lists separated."""
from pathlib import Path
import argparse,json,math,hashlib
import numpy as np
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate');p.add_argument('--output',required=True);p.add_argument('--count',type=int,default=2000);p.add_argument('--orders',type=int,default=4);a=p.parse_args();R=Path('/home/sato/ahc074/runs')
def read(rid):
 d=R/rid;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
 cases=sorted(json.loads((d/'result.json').read_text())['cases'],key=lambda c:int(c['seed']))
 assert [int(c['seed']) for c in cases]==list(range(a.count))
 x=np.array([c['order_scores'] for c in cases]);assert x.shape==(a.count,a.orders) and np.all(x>0)
 return x,hashlib.sha256((d/'src/main.cpp').read_bytes()).hexdigest()
b,bh=read(a.reference);c,ch=read(a.candidate)
def stat(x):return dict(n=len(x),mean=float(np.mean(x)),se=float(np.std(x,ddof=1)/math.sqrt(len(x))))
out={'reference':a.reference,'candidate':a.candidate,'hashes':[bh,ch],'groups':{}}
for label,lo,hi in [('all',0,a.count),('train',0,500),('500-999',500,1000),('500-1999',500,a.count),('0-999',0,1000),('1000-1999',1000,a.count)]:
 if hi>a.count or hi<=lo:continue
 out['groups'][label]={}
 for lists,jj in [('all',list(range(a.orders))),('real',[0]),('new',list(range(1,a.orders)))]:
  if not jj:continue
  log=(100*np.log(c[lo:hi,jj]/b[lo:hi,jj])).mean(axis=1);moves=((c[lo:hi,jj]-b[lo:hi,jj])/1024).mean(axis=1)
  out['groups'][label][lists]={'pct':stat(log),'moves':stat(moves),'wtl':[int(sum(log<0)),int(sum(log==0)),int(sum(log>0))]}
  print(label,lists,out['groups'][label][lists])
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
