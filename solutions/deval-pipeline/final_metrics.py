"""Frozen final normal comparison, held-out replay, and output/annotation audits."""
from pathlib import Path
import json,sys,math,hashlib,argparse
R=Path('/home/sato/ahc074/runs');root=Path(__file__).resolve().parents[2]
def mean(a):return sum(a)/len(a)
def se(a):m=mean(a);return (sum((x-m)**2 for x in a)/(len(a)-1)/len(a))**.5
def quantile(a,q):v=sorted(a);i=q*(len(v)-1);lo=int(i);return v[lo]+(i-lo)*(v[min(lo+1,len(v)-1)]-v[lo])
def load(run,n):
 p=R/run;m=json.loads((p/'meta.json').read_text());assert m['status']=='ok'
 d={int(c['seed']):c for c in json.loads((p/'result.json').read_text())['cases']};assert len(d)==n and all(c['score']>0 for c in d.values())
 metrics={int(k):v for k,v in json.loads((p/'metrics.json').read_text())['cases'].items()};assert sorted(d)==sorted(metrics)
 return d,metrics,m
p=argparse.ArgumentParser();p.add_argument('solution');p.add_argument('--normal',nargs='+',required=True);p.add_argument('--replay',required=True);p.add_argument('--reference',default='20261107-134239_deval-ordered8');a=p.parse_args();outdir=root/'solutions'/a.solution
runs={r:load(r,2000) for r in a.normal};reference=a.normal[0];candidate=next(r for r in a.normal if r.endswith('_'+a.solution));out={'normal':{},'paired_scores':{},'replay':{},'audit':{}}
def judge(s):return 1.04*s['helper_end_sec']+1.35*s['req_sec']+s['end_sec']-s['helper_end_sec']-s['req_sec']
for run,(d,m,meta) in runs.items():
 seeds=sorted(d);assert seeds==list(range(2000));s=[m[i]['stderr'] for i in seeds];j=[judge(x) for x in s];e=[x['end_sec'] for x in s];t=[d[i]['execution_time'] for i in seeds]
 z={'n':len(s),'score_mean':mean([d[i]['score'] for i in seeds]),'judge':{'mean':mean(j),'p99':quantile(j,.99),'max':max(j),'over_1_9':sum(x>1.9 for x in j),'over_2':sum(x>2 for x in j)},'end_sec':{'mean':mean(e),'p99':quantile(e,.99),'max':max(e),'over_1_8':sum(x>1.8 for x in e),'over_1_9':sum(x>1.9 for x in e),'over_2':sum(x>2 for x in e)},'wall_sec':{'mean':mean(t),'p99':quantile(t,.99),'max':max(t)},'stage_mean':{k:mean([x[k] for x in s]) for k in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','initial_order_sec','helper_end_sec','req_sec'] if all(k in x for x in s)},'outside_load':meta.get('outside_load'),'errors':{k:sum(m[i]['stderr'].get(k,0) for i in seeds) for k in ['self_wrong','op_label_errors','plan_failures','unsafe_plans']},'E':sum(m[i]['E'] for i in seeds)}
 if all('dv_candidates' in y for y in s):
  import collections
  z['candidate_counts']=dict(collections.Counter(int(y['dv_candidates']) for y in s))
  z['chosen_counts']=dict(collections.Counter(int(y['dv_chosen']) for y in s))
 old=[judge(runs[reference][1][i]['stderr']) for i in seeds];ratio=mean(j)/mean(old);influence=[(x-ratio*y)/mean(old) for x,y in zip(j,old)];z['judge_ratio_old']=[ratio,se(influence)];out['normal'][run]=z
 for ref,(bd,_,_) in runs.items():
  if ref==run:continue
  v=[100*math.log(d[i]['score']/bd[i]['score']) for i in seeds];out['paired_scores'][run+' vs '+ref]={'mean':mean(v),'se':se(v),'wtl':[sum(x<0 for x in v),sum(x==0 for x in v),sum(x>0 for x in v)]}
ordered=next(r for r in a.normal if r.endswith('_deval-ordered8'))
out['stage_deltas_vs_ordered8']={}
for key in ['map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','helper_end_sec','req_sec']:
 values=[runs[candidate][1][i]['stderr'][key]-runs[ordered][1][i]['stderr'][key] for i in range(2000)]
 out['stage_deltas_vs_ordered8'][key]=[mean(values),se(values)]
b,_,_=load(a.reference,500);c,cm,_=load(a.replay,500);assert sorted(b)==sorted(c)==list(range(500,1000))
for name,sl in [('fresh',slice(1,8)),('all',slice(0,8)),('real',slice(0,1))]:
 v=[];moves=[]
 for i in sorted(c):
  assert len(c[i]['order_scores'])==8 and min(c[i]['order_scores'])>0
  x=mean(b[i]['order_scores'][sl]);y=mean(c[i]['order_scores'][sl]);v.append(100*math.log(y/x));moves.append((y-x)/1024)
 out['replay'][name]={'mean':mean(v),'se':se(v),'moves_per_order':mean(moves),'wtl':[sum(x<0 for x in v),sum(x==0 for x in v),sum(x>0 for x in v)]}
assert all(z['E']==0 and not any(z['errors'].values()) for z in out['normal'].values())
source=(outdir/'main.cpp').read_bytes();assert source==(R/candidate/'src/main.cpp').read_bytes()==(R/a.replay/'src/main.cpp').read_bytes();assert len(source)<=522000
same=sum((R/candidate/'out'/f'{i:04d}.txt').read_bytes()==(R/a.replay/'out'/f'{i:04d}.txt').read_bytes() for i in range(500,1000));assert same==500
out['audit']={'source_bytes':len(source),'sha256':hashlib.sha256(source).hexdigest(),'frozen_source_identical':True,'normal_replay_list0_identical':same,'replay_requests':4000*1024,'replay_error_counts':{}}
import re
keys=['self_wrong','op_label_errors','plan_failures','unsafe_plans'];totals=dict.fromkeys(keys,0);matched=0
for order in range(8):
 ep=R/a.replay/('err' if order==0 else f'orders/{order}/err');fs=list(ep.glob('*.txt'));assert len(fs)==500
 for f in fs:
  data=f.read_text()
  for key in keys:
   vals=re.findall(r'^'+key+r' = (\S+)$',data,re.M);assert vals;totals[key]+=int(float(vals[-1]))
  seen=set();moves=0
  for match in re.finditer(r'^@ops (\d+) = ?(.*)$',data,re.M):
   q=int(match.group(1));assert q not in seen;seen.add(q)
   for token in match.group(2).split():
    _,sep,n=token.partition('*');moves+=int(n) if sep else 1
  assert seen==set(range(1024)) and moves==c[int(f.stem)]['order_scores'][order],(f,moves)
  matched+=1
out['audit']['replay_error_counts']=totals
out['audit']['replay_trace_moves_match_score']=matched
assert matched==4000 and not any(totals.values()),totals
out['run_ids']={'normal':a.normal,'replay':a.replay,'reference':a.reference}
(outdir/'final-metrics.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
