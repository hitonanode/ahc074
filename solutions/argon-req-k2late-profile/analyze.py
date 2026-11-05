from pathlib import Path
import re,json,statistics as st,subprocess
r=Path('/home/sato/ahc074/runs');p=Path('solutions/argon-req-k2late-profile');base=r/'20261106-061359_argon-req-k2late-fast';cand=r/'20261106-061359_argon-req-k2late-profile'
rows=[]
for f in sorted(cand.glob('out/*.txt'))+sorted(cand.glob('orders/*/out/*.txt')):
 rel=f.relative_to(cand); assert f.read_bytes()==(base/rel).read_bytes(),rel
 e=rel.parent.parent/'err'/rel.name;t=(cand/e).read_text();b=(base/e).read_text()
 def norm(t):return [l for l in t.splitlines() if not re.match(r'^(joint_profile_|\w+_sec\s*=)',l)]
 assert norm(t)==norm(b),e
 rows.append({k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',t,re.M)})
fields=['trials','ejects','accepts','gain','saved','edit_sec','eject_sec']
data=[{key:st.mean(x[f'joint_profile_{i}_{key}'] for x in rows) for key in fields} for i in range(64)]
(p/'profile.json').write_text(json.dumps(data,indent=2)+'\n')
print(len(rows),'outputs and non-time stderr excluding new profile identical',flush=True)
for feature,fn,values in [('gap',lambda i:i%4,range(4)),('repeated',lambda i:(i//4)%2,range(2)),('new_paper',lambda i:(i//8)%2,range(2)),('length',lambda i:i//16,range(4))]:
 for value in values:
  d={k:sum(v[k] for i,v in enumerate(data) if fn(i)==value) for k in fields}
  print(feature,value,d,flush=True)
print('bins with gains',flush=True)
for i,d in enumerate(data):
 if d['gain']>0:print(i,d,flush=True)
with (p/'wide-analysis.log').open('w') as f:
 subprocess.run(['python3','solutions/argon-req-completeold/analyze.py','20261106-061020_argon-req-ejectstats-v2','20261106-061020_argon-req-k2late-fast','20261106-061021_argon-req-k2late-wide','20261106-061021_argon-req-k2late-all','--end','200','--json',str(p/'wide-results.json')],stdout=f,check=True)
