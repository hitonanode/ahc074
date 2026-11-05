"""Check saved stdout and all non-timing stderr lines between two runs."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--end',type=int,default=200)
p.add_argument('--ignore-prefix',default='');p.add_argument('--output',default='fast-identity.json');a=p.parse_args()
root=Path('/home/sato/ahc074/runs');rows=[]
def stable(path):
    return [line for line in path.read_text().splitlines()
            if not re.match(r'^\s*\S*(?:_sec|_ms)\S*\s*=',line) and not (a.ignore_prefix and line.startswith(a.ignore_prefix))]
for seed in range(a.end):
    f=f'{seed:04d}.txt';x=root/a.base;y=root/a.candidate
    eq=(x/'out'/f).read_bytes()==(y/'out'/f).read_bytes()
    sx,sy=stable(x/'err'/f),stable(y/'err'/f)
    rows.append(dict(seed=seed,stdout=eq,stderr=sx==sy))
    if sx!=sy:
        print('stderr difference',seed,[(l,r)for l,r in zip(sx,sy)if l!=r][:5])
result=dict(base=a.base,candidate=a.candidate,n=a.end,stdout_identical=sum(r['stdout']for r in rows),stderr_identical=sum(r['stderr']for r in rows),rows=rows)
(Path(__file__).resolve().parent/a.output).write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items()if k!='rows'})
assert all(r['stdout']and r['stderr']for r in rows)
