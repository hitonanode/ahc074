from pathlib import Path
import json,math,statistics,sys
ROOT=Path('/home/sato/ahc074/runs')
def load(run):
 data=json.loads((ROOT/run/'result.json').read_text());return {int(r['seed']):r for r in data['cases']}
def stats(values):
 return dict(cases=len(values),difference=100*statistics.mean(values),se=100*statistics.stdev(values)/math.sqrt(len(values)),wins=sum(x<0 for x in values),ties=sum(x==0 for x in values),losses=sum(x>0 for x in values))
def compare(base,candidate):
 a,b=load(base),load(candidate);seeds=sorted(a.keys()&b.keys());good=[s for s in seeds if a[s]['score']>0 and b[s]['score']>0]
 result=stats([math.log(b[s]['score']/a[s]['score']) for s in good]);result.update(runs=[base,candidate],means=[statistics.mean(v[s]['score']for s in good)for v in [a,b]],wa=[sum(v[s]['score']==0 for s in seeds)for v in[a,b]],over_two=[sum(v[s]['execution_time']>2 for s in seeds)for v in[a,b]])
 metrics=json.loads((ROOT/candidate/'metrics.json').read_text())['cases'];result['metrics']={}
 for key in ['self_wrong','plan_failures','unsafe_plans','fast_requests','req_sec','end_sec','perforation_holes']:
  v=[r['stderr'][key]for r in metrics.values()if key in r.get('stderr',{})]
  result['metrics'][key]=dict(mean=statistics.mean(v),max=max(v),sum=sum(v)) if v else None
 return result
if __name__=='__main__':
 result=compare(*sys.argv[1:3]);print(json.dumps(result,indent=2))
 if len(sys.argv)>3:Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
