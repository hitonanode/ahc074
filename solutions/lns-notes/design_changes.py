"""Physical window, shared-pair, column and perforation changes of selected designs."""
from pathlib import Path
import argparse,json,statistics,collections
R=Path('/home/sato/ahc074/runs')
def parse(p):
 a={}
 for line in p.read_text().split('\nstderr ')[0].splitlines():
  v=line.split()
  if v[0] in ['permutation','edge','polarity','ded','columns','handle','A','papers']:a[v[0]]=list(map(int,v[2:]))
  elif v[0] in ['M','G','H']:a[v[0]]=int(v[1])
 return a
def features(a):
 windows=[None]*64
 for j in range(a['G']):windows[a['permutation'][j]]=(tuple(a['edge'][2*j:2*j+2]),a['polarity'][j])
 members=collections.defaultdict(list)
 for t,k in enumerate(a['ded']):members[k].append(t)
 pairs={tuple(v) for v in members.values() if len(v)==2};sizes=collections.Counter(c for c in a['columns'] if c>=0)
 extra=0
 for k,ts in members.items():
  col=a['columns'][k];natural=sum(1<<a['handle'][j] for j in range(col+1))
  if len(ts)==2:natural&=~(a['A'][ts[0]]^a['A'][ts[1]])
  extra+=(natural&~a['papers'][2*k]).bit_count()
 return windows,pairs,sizes,extra,[a['permutation'][h] for h in a['handle']]
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--output',required=True);a=p.parse_args();b=R/a.base;c=R/a.candidate
for d in [b,c]:assert json.loads((d/'meta.json').read_text())['status']=='ok'
rows=[]
for f in (c/'design').glob('*.txt'):
 x=features(parse(b/'design'/f.name));y=features(parse(f));row={}
 row['windows_changed']=sum(u!=v for u,v in zip(x[0],y[0]));row['generic_handle_changed']=sum((u is None)!=(v is None) for u,v in zip(x[0],y[0]));row['polarity_only']=sum(u is not None and v is not None and u[0]==v[0] and u[1]!=v[1] for u,v in zip(x[0],y[0]));row['new_pairs']=len(y[1]-x[1]);row['column_size_l1']=sum(abs(y[2][k]-x[2][k]) for k in x[2].keys()|y[2].keys());row['extra_hole_delta']=y[3]-x[3];row['handle_order_changes']=sum(u!=v for u,v in zip(x[4],y[4]));rows.append(row)
out={'n':len(rows),'means':{k:statistics.mean([r[k] for r in rows]) for k in rows[0]},'windows_changed_cases':sum(r['windows_changed']>0 for r in rows),'window_histogram':dict(collections.Counter(r['windows_changed'] for r in rows))}
sel=[r for r in rows if r['windows_changed']>0]
out['conditional_on_window_change']={k:statistics.mean([r[k] for r in sel]) for k in rows[0]} if sel else {}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
