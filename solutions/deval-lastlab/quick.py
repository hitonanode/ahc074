from pathlib import Path
import sys,json,math
R=Path('/home/sato/ahc074/runs')
def load(r):
 p=R/r;assert json.loads((p/'meta.json').read_text())['status']=='ok'
 return {int(c['seed']):c for c in json.loads((p/'result.json').read_text())['cases']}
def ms(a):
 m=sum(a)/len(a);return [m,(sum((x-m)**2 for x in a)/len(a)/(len(a)-1))**.5]
def avg(a):return sum(a)/len(a)
b=load(sys.argv[1])
for run in sys.argv[2:]:
 c=load(run);seeds=sorted(set(c)&set(b));assert seeds and max(seeds)<500
 out={'run':run,'n':len(seeds)}
 for tag,sl in [('fresh',slice(1,None)),('all',slice(None)),('real',slice(0,1))]:
  if tag=='fresh' and len(c[seeds[0]].get('order_scores',[]))<2:continue
  v=[100*math.log(avg(c[i].get('order_scores',[c[i]['score']])[sl])/avg(b[i].get('order_scores',[b[i]['score']])[sl])) for i in seeds]
  out[tag]=ms(v)
 print(json.dumps(out))
