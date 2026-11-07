"""Check initial-order variants are only permutations within each column."""
from pathlib import Path
import json,sys,collections
R=Path('/home/sato/ahc074/runs')
def load(f):
 d={}
 for line in f.read_text().splitlines():
  x=line.split()
  if x and x[0]=='stderr':break
  if x and x[0] in ['M','G','H']:d[x[0]]=int(x[1])
  if x and x[0] in ['permutation','A','edge','polarity','papers','columns','ded','handle']:d[x[0]]=list(map(int,x[2:]))
 d['papers']=list(zip(d['papers'][::2],d['papers'][1::2]));return d
ref=R/sys.argv[1]/'design';outputs=[]
for run in sys.argv[2:]:
 p=R/run/'design';files=sorted(p.glob('*.txt'));assert len(files)==500
 for f in files:
  a=load(ref/f.name);b=load(f)
  for key in ['M','G','H','permutation','A','edge','polarity','columns','handle']:assert a[key]==b[key],(run,f.name,key)
  for c in range(-1,a['H']):assert collections.Counter(x for x,col in zip(a['papers'],a['columns']) if col==c)==collections.Counter(x for x,col in zip(b['papers'],b['columns']) if col==c)
  for x,y in zip(a['ded'],b['ded']):assert a['papers'][x]==b['papers'][y] and a['columns'][x]==b['columns'][y]
 outputs.append({'run':run,'designs':len(files),'column_paper_multisets_equal':True,'ded_patterns_equal':True})
print(json.dumps(outputs,indent=2));Path(__file__).with_name('initial-design-check.json').write_text(json.dumps(outputs,indent=2)+'\n')
