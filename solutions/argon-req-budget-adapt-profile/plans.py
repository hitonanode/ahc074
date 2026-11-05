from pathlib import Path
import collections
r=Path('/home/sato/ahc074/runs/20261106-075852_argon-req-budget-adapt-profile')
groups=collections.defaultdict(lambda:[0,0.,0.,0.]);n=0
for f in list(r.glob('err/*.txt'))+list(r.glob('orders/*/err/*.txt')):
 n+=1;times=collections.defaultdict(float);rows=[]
 for line in f.read_text().splitlines():
  v=line.split()
  if line.startswith('#f3post ') and int(v[2])==3:times[int(v[1])]+=float(v[9])
  if line.startswith('#f2plan '):rows.append(v)
 for v in rows:
  gap=float(v[6]);gain=float(v[8]);won=int(v[9]);sec=times[int(v[1])]
  for threshold in [0,.1,.25,.5,1,2,5,1e9]:
   if gap<=threshold:
    z=groups[threshold];z[0]+=1;z[1]+=won;z[2]+=max(0,gain);z[3]+=sec
print('files',n,'threshold: calls wins gain seconds')
for k,v in groups.items():print(k,*[x/n for x in v])
