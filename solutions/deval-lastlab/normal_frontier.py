"""Training-only normal timing comparisons; all candidates use identical fixed budgets across seeds."""
from pathlib import Path
import re,json,math,sys
P=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
def mean(v):return sum(v)/len(v)
def se(v):m=mean(v);return (sum((x-m)**2 for x in v)/(len(v)-1)/len(v))**.5
def quantile(v,q):v=sorted(v);x=q*(len(v)-1);i=int(x);return v[i]+(x-i)*(v[min(i+1,len(v)-1)]-v[i])
def judge(x):return 1.04*x['helper_end_sec']+1.35*x['req_sec']+x['end_sec']-x['helper_end_sec']-x['req_sec']
result=[]
for name in sys.argv[1:]:
 p=P/name;ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)',p.read_text(),re.M)
 data={}
 for r in ids:
  q=R/r;meta=json.loads((q/'meta.json').read_text());assert meta['status']=='ok'
  cs={int(c['seed']):c for c in json.loads((q/'result.json').read_text())['cases']};assert sorted(cs)==list(range(500))
  ms={int(i):c['stderr'] for i,c in json.loads((q/'metrics.json').read_text())['cases'].items()}
  ts=[judge(ms[i]) for i in range(500)]
  data[r]={'scores':cs,'metrics':ms,'ts':ts,'load':meta.get('outside_load')}
 old=next(r for r in ids if r.endswith('_argon-des-perf-latew105'));nofb=next(r for r in ids if r.endswith('_deval-vbranch-nofb'));base=next(r for r in ids if r.endswith('_deval-flex125-plan3'))
 for r,d in data.items():
  if r in [old,nofb,base]:continue
  v=[100*math.log(d['scores'][i]['score']/data[base]['scores'][i]['score']) for i in range(500)]
  z={'log':name,'run':r,'normal_delta':[mean(v),se(v)],'judge_mean':mean(d['ts']),'ratio_old':mean(d['ts'])/mean(data[old]['ts']),'p99':quantile(d['ts'],.99),'p99_nofb':quantile(data[nofb]['ts'],.99),'max':max(d['ts']),'load':d['load']}
  for k in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec']:
   v=[d['metrics'][i][k]-data[base]['metrics'][i][k] for i in range(500)];z[k]=[mean(v),se(v)]
  result.append(z)
(P/'normal-frontier.json').write_text(json.dumps(result,indent=2)+'\n')
for z in result:print(json.dumps(z))
