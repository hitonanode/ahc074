"""Read completed profiles/calibration, under flock + nice; generate the budget table."""
from pathlib import Path
import json,re,math
import numpy as np
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def stats(v):
 a=np.asarray(v,float)
 return dict(mean=float(a.mean()),se=float(a.std(ddof=1)/np.sqrt(len(a))),p99=float(np.percentile(a,99)),max=float(a.max()))
def read_run(rid):
 d=R/rid;m=json.loads((d/'meta.json').read_text());assert m['status']=='ok'
 cs=json.loads((d/'result.json').read_text())['cases'];assert all(c['score']>0 for c in cs)
 rows=[{k:float(v)for k,v in rx.findall((d/'err'/f"{int(c['seed']):04d}.txt").read_text())}for c in cs]
 return rows,m
out={'profiles':{},'calibration':{}}
for compiler in ['gcc','clang']:
 x=json.loads((N/f't13-profile-{compiler}.json').read_text());rid,v=next(iter(x['results'].items()))
 assert v['identity']['same']==v['identity']['total']==200
 rows,m=read_run(rid)
 keys=sorted(set.intersection(*(set(q)for q in rows)))
 phases={k[3:-4]:stats([q[k]for q in rows])for k in keys if k.startswith('dt_')and k.endswith('_sec')}
 out['profiles'][compiler]={'run':rid,'reference':x['reference'],'identity':v['identity'],'phases':phases,
  'parent_times':{k:v['metrics'][k]['reference'] for k in ['helper_end_sec','req_sec','end_sec']},
  'profile_times':{k:v['metrics'][k] for k in ['helper_end_sec','req_sec','end_sec']},
  'clock_ns':stats([q['dt_clock_ns']for q in rows]),'outside_load':m.get('outside_load')}
sequence=['map_setup','map_search','map_reset','gopt','map_return','initialize','anneal_s0','anneal_s1']
for i in range(9):
 if i<4:sequence += [f'c{i}_anneal_s2',f'c{i}_anneal_s3']
 if i in [0,1,2,3,4,6]:sequence += [f'c{i}_filler',f'c{i}_match']
 sequence += [f'c{i}_print',f'c{i}_perforation',f'c{i}_late_match',f'c{i}_value']
sequence += ['initial_order','helpers']
weights=[]
for key in sequence:
 weights.append(sum(out['profiles'][c]['phases'][key]['mean']for c in ['gcc','clang'])/2)
den=sum(weights)
out['schedule']=[{'name':k,'seconds':w,'share':w/den,'cumulative':sum(weights[:i+1])/den}for i,(k,w)in enumerate(zip(sequence,weights))]
out['schedule_sum_sec']=den
out['same_estimate_sec']=sum(out['profiles'][c]['parent_times']['helper_end_sec']['mean']for c in ['gcc','clang'])/2
for d in sorted(R.glob('20261108-220933_dcomp-combo-dual25*')):
 rows,m=read_run(d.name)
 out['calibration'][d.name]={'command':m['compile_command'],'count':len(rows),'times':{k:stats([q[k]for q in rows])for k in ['map_end_sec','helper_end_sec','req_sec','end_sec']},
  'seed0':rows[0] if int(json.loads((d/'result.json').read_text())['cases'][0]['seed'])==0 else None}
for rid in ['20261108-224255_dcomp-combo-dual30','20261108-230504_dcomp-combo-dual30']:
 rows,m=read_run(rid)
 out['calibration'][rid]={'count':len(rows),'times':{k:stats([q[k]for q in rows])for k in ['helper_end_sec','req_sec','end_sec']},
 'rest':stats([q['end_sec']-q['helper_end_sec']-q['req_sec']for q in rows])}
(N/'t13-shares.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# Task13 設計の段別時間','',f'GCC既定・Clang nativeそれぞれ200ケース。両compilerとも親と200/200 stdout一致。比率は両者の段別平均の等重み平均から作成。境界計測を入れた版の比率なので、計測なしの親の総時間も別に示す。','','|段|GCC ms|Clang ms|共通比率 %|累積 %|','|---|---:|---:|---:|---:|']
for item in out['schedule']:
 k=item['name'];g=out['profiles']['gcc']['phases'][k]['mean']*1000;c=out['profiles']['clang']['phases'][k]['mean']*1000
 lines.append(f"|{k}|{g:.4f}|{c:.4f}|{item['share']*100:.5f}|{item['cumulative']*100:.5f}|")
(N/'SHARES13.md').write_text('\n'.join(lines)+'\n')
print('parent same estimate',out['same_estimate_sec'],'phase total',den)
for c,v in out['profiles'].items():print(c,v['run'],'parent',v['parent_times'],'clock_ns',v['clock_ns'],'load',v['outside_load'])
