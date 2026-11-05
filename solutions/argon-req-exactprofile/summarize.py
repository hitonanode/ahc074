from pathlib import Path
import sys,re,collections,json,statistics as st
root=Path('/home/sato/ahc074/runs')
results={}
for name in sys.argv[1:]:
 r=root/name
 sums=collections.defaultdict(list);ops=collections.defaultdict(lambda:[0.]*6);n=0
 for f in sorted(r.glob('err/*.txt'))+sorted(r.glob('orders/*/err/*.txt')):
  n+=1
  for line in f.read_text().splitlines():
   m=re.fullmatch(r'(\w+) = ([-+0-9.eE]+)',line)
   if m:sums[m[1]].append(float(m[2]))
   if line.startswith('#f3op '):
    v=line.split();key=(int(v[2]),int(v[7]))
    for j in range(6):ops[key][j]+=float(v[8+j])
 means={k:st.mean(v) for k,v in sums.items()}
 results[name]={'files':n,'metrics':means,'f3':{str(k):[v/n for v in vs] for k,vs in sorted(ops.items())}}
 print(name,'files',n)
 for k,v in means.items():
  if k.startswith('cfprof_') and k.endswith('_exc'):print(k,round(v*1000,3),'ms',means.get(k[:-4]+'_calls'))
 print('req',means.get('req_sec'),'post inc',means.get('cfprof_post_inc'))
 print('F3 stage op: trials legal accepts gain saved sec')
 for k,v in sorted(ops.items()):print(k,*[round(x/n,6) for x in v])
Path(__file__).with_name('profile-summary.json').write_text(json.dumps(results,indent=2)+'\n')
