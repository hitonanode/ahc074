from pathlib import Path
import argparse,json,re,math,statistics,hashlib
p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',required=True);a=p.parse_args()
root=Path('/home/sato/ahc074/runs');rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def stat(v):
 return {'n':len(v),'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0,'min':min(v),'max':max(v)}
def load(r):
 d=root/r;m=json.loads((d/'meta.json').read_text());c={int(x['seed']):x for x in json.loads((d/'result.json').read_text())['cases']};logs={i:dict((k,float(v)) for k,v in rx.findall((d/'err'/f'{i:04d}.txt').read_text())) for i in c};return d,m,c,logs
b,bm,bc,bl=load(a.runs[0]);out={'base':a.runs[0],'comparisons':{}}
for r in a.runs[1:]:
 d,m,c,l=load(r);ss=sorted(c.keys()&bc.keys());good=[i for i in ss if c[i]['score'] and bc[i]['score']];ratio=[math.log(c[i]['score']/bc[i]['score'])*100 for i in good]
 z={'n':len(ss),'wa':len(ss)-len(good),'score':stat(ratio),'wtl':[sum(c[i]['score']<bc[i]['score'] for i in good),sum(c[i]['score']==bc[i]['score'] for i in good),sum(c[i]['score']>bc[i]['score'] for i in good)],'stdout_identical':sum((d/'out'/f'{i:04d}.txt').read_bytes()==(b/'out'/f'{i:04d}.txt').read_bytes() for i in ss),'paired_ms':{},'counters':{},'outside_load':m.get('outside_load')}
 for k in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec','end_sec']:
  if all(k in l[i] and k in bl[i] for i in ss):z['paired_ms'][k]=stat([1000*(l[i][k]-bl[i][k]) for i in ss])
 keys=set.union(*(set(l[i]) for i in ss))
 for k in sorted(keys):
  if k.startswith(('ia_','f2_memo','dp_post_memo','cf_value','partial_mdp','colmdp_columns','generic_memo')):z['counters'][k]=stat([l[i][k] for i in ss if k in l[i]])
 out['comparisons'][r]=z
 print(r,'score',z['score'],'wtl',z['wtl'],'identical',z['stdout_identical'])
 print('times',{k:(round(v['mean'],3),round(v['se'],3)) for k,v in z['paired_ms'].items()})
 print('counters',{k:round(v['mean'],3) for k,v in z['counters'].items() if k.startswith(('ia_endmemo','ia_ret'))})
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
