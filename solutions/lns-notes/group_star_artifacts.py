"""Group captured native finishes by V, without observing request results.

The star implementation records each of three finishes, not the local winner.
This reconstructs that winner from the recorded V values. No design is modified.
"""
from pathlib import Path
import argparse, json, re, shutil

p=argparse.ArgumentParser()
p.add_argument('directory');p.add_argument('--output',required=True)
p.add_argument('--steps',type=int,default=4)
a=p.parse_args();root=Path(a.directory);dest=Path(a.output)
assert not dest.exists();dest.mkdir(parents=True)
names=sorted(x.name for x in (root/'candidate-000/design').glob('*.txt'))
assert names

def read(cid,name):
    p=root/f'candidate-{cid:03d}/design'/name
    if not p.exists():return None
    t=p.read_text();v=float(re.search(r'^lns_export_v = (\S+)$',t,re.M)[1])
    return v,t,cid

def save(cid,name,item,failed=False):
    v,t,origin=item;body=t.split('\nstderr ')[0]+'\n'
    msg=f'lns_export_id = {cid}\nlns_export_failure = {int(failed)}\nlns_export_v = {v:.17g}\n'
    p=dest/f'candidate-{cid:03d}/design'/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(body+f'stderr {len(msg)}\n'+msg)
    return {'file':name,'candidate':cid,'original_candidate':origin,'v':v,'failed':failed}

records=[]
for name in names:
    base=[read(i,name) for i in range(8)];assert all(x is not None for x in base)
    incumbent=min(base,key=lambda x:x[0])
    for i in range(4):records.append(save(i,name,base[i]))
    records.append(save(1000,name,incumbent))
    for j in range(a.steps):
        opts=[x for i in range(8+3*j,11+3*j) if (x:=read(i,name)) is not None]
        assert len(opts) in [0,3],(j,name,len(opts))
        chosen=min(opts,key=lambda x:x[0]) if opts else incumbent
        records.append(save(2000+j,name,chosen,not opts))
        incumbent=min([incumbent,chosen],key=lambda x:x[0])
(dest/'grouping.json').write_text(json.dumps(records,indent=2)+'\n')
print('cases',len(names),'records',len(records))
