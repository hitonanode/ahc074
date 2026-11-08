from pathlib import Path
import argparse,json,statistics,collections,re
R=Path('/home/sato/ahc074/runs')
def parse(p):
 a={}
 for line in p.read_text().split('\nstderr ')[0].splitlines():
  v=line.split()
  if v[0] in ['permutation','edge','polarity','ded','columns','handle','A','papers']:a[v[0]]=list(map(int,v[2:]))
  elif v[0] in ['M','G','H']:a[v[0]]=int(v[1])
 return a
def windows(a):
 out=[None]*64
 for j in range(a['G']):out[a['permutation'][j]]=(tuple(a['edge'][2*j:2*j+2]),a['polarity'][j])
 return out
def pairs(a):
 groups=collections.defaultdict(list)
 for t,k in enumerate(a['ded']):groups[k].append(t)
 return {tuple(v) for v in groups.values() if len(v)==2}
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('runs',nargs='+');a=p.parse_args();ref=R/a.reference
for run in a.runs:
 d=R/run;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
 rows=[]
 for f in (d/'design').glob('*.txt'):
  b=parse(ref/'design'/f.name);c=parse(f);ws=sum(x!=y for x,y in zip(windows(b),windows(c)));new=len(pairs(c)-pairs(b))
  rows.append((ws,new))
 print(run,len(rows),json.dumps({'windows_changed_cases':sum(w>0 for w,n in rows),'window_changes_mean':statistics.mean([w for w,n in rows]),'new_pairs_mean':statistics.mean([n for w,n in rows]),'new_pairs_when_windows_changed':statistics.mean([n for w,n in rows if w>0]) if any(w>0 for w,n in rows) else None,'windows_hist':dict(collections.Counter(w for w,n in rows))}))
