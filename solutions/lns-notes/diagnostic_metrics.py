"""Within-case V ranking/noise correction and before/after finishing on exported designs."""
from pathlib import Path
import argparse,json,re,math
import numpy as np
R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('replay_table');p.add_argument('--output',required=True);a=p.parse_args()
rows=json.loads(Path(a.replay_table).read_text());data={};values={};byid={};failures={};verified_requests=0
for row in rows:
 src=Path(row['source']);meta=json.loads((src/'meta.json').read_text());cid=meta['candidate_id'];run=R/row['replay'];m=json.loads((run/'meta.json').read_text());assert m['status']=='ok'
 cs=json.loads((run/'result.json').read_text())['cases'];assert all(min(c['order_scores'])>0 for c in cs)
 data[cid]={int(c['seed']):np.array(c['order_scores'],float)/1024 for c in cs};values[cid]={};failures[cid]={}
 for c in cs:
  t=(run/'err'/f"{c['seed']:04d}.txt").read_text();v=re.findall(r'^lns_export_v = (\S+)$',t,re.M);assert len(v)==1;values[cid][int(c['seed'])]=float(v[0])
  f=re.findall(r'^lns_export_failure = (\S+)$',t,re.M);assert len(f)==1;failures[cid][int(c['seed'])]=int(f[0])
  for j,score in enumerate(c['order_scores']):
   trace=t if j==0 else (run/f"orders/{j}/err/{c['seed']:04d}.txt").read_text()
   ops=re.findall(r'^@ops \d+ = *(.*)$',trace,re.M);assert len(ops)==1024,(cid,c['seed'],j,len(ops))
   moves=sum(int(token.partition('*')[2]) if '*' in token else 1 for line in ops for token in line.split())
   assert moves==score,('trace cost != score',cid,c['seed'],j,moves,score)
   for key in ['self_wrong','op_label_errors','plan_failures','unsafe_plans']:
    vals=re.findall(r'^'+key+r' = (\S+)$',trace,re.M);assert vals and float(vals[-1])==0,(cid,c['seed'],j,key,vals)
   verified_requests+=1024
 byid[cid]=row
out={'groups':{},'finishing':{},'sources':byid,'failed_repair_exports':{k:sum(v.values()) for k,v in failures.items()},'trace_verified_requests':verified_requests,'all_trace_moves_equal_scores':True}
def stat(x):
 x=np.array(x,float);return {'n':len(x),'mean':float(x.mean()),'se':float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0}
def center(x):return (x-x.mean(axis=1,keepdims=True)).ravel()
def corr(x,y):return float(np.corrcoef(x,y)[0,1])
for label,ids in [('branches',[x for x in range(4) if x in data]),('lns_finished',[x for x in range(2000,2010) if x in data]),('lns_with_base',[x for x in [1000,*range(2000,2010)] if x in data]),('lns_raw',[x for x in range(3000,3010) if x in data])]:
 if len(ids)<2:continue
 ss=sorted(set.intersection(*(set(data[x]) for x in ids)));y=np.array([[data[c][s] for c in ids] for s in ss]);v=np.array([[values[c][s] for c in ids] for s in ss])
 yc=center(y.mean(axis=2));vc=center(v)
 if np.dot(vc,vc)<1e-16 or np.dot(yc,yc)<1e-16:
  out['groups'][label]={'n_cases':len(ss),'ids':ids,'status':'no_within_case_variation'};continue
 rho=corr(center(y[:,:,:4].mean(axis=2)),center(y[:,:,4:].mean(axis=2)));rel=2*rho/(1+rho);r=corr(vc,yc)
 slope=float(np.dot(vc,yc)/np.dot(vc,vc));pick=v.argmin(axis=1);oracle=y[:,:,:4].mean(axis=2).argmin(axis=1);idx=np.arange(len(ss));hold=y[:,:,4:].mean(axis=2)
 out['groups'][label]={'n_cases':len(ss),'ids':ids,'r':r,'half_r':rho,'reliability':rel,'corrected_r':r/np.sqrt(rel) if rel>0 else None,'within_case_slope':slope,'centered_rmse':float(np.sqrt(np.mean((vc-yc)**2))),'absolute_bias_V_minus_real':float(np.mean(v-y.mean(axis=2))),'V_pick_vs_random_lists4_7':stat(hold[idx,pick]-hold.mean(axis=1)),'oracle_vs_random_lists4_7':stat(hold[idx,oracle]-hold.mean(axis=1))}
 out['groups'][label]['observed_within_case_sd']=float(np.sqrt(np.mean(yc**2)))
 out['groups'][label]['noise_corrected_within_case_sd']=float(np.sqrt(np.mean(yc**2)*rel)) if rel>0 else None
 fresh=center(y[:,:,1:].mean(axis=2));six=center(y[:,:,1:7].mean(axis=2))
 hr6=corr(center(y[:,:,1:4].mean(axis=2)),center(y[:,:,4:7].mean(axis=2)));rel6=2*hr6/(1+hr6);r6=corr(vc,six)
 out['groups'][label]['fresh_lists1_7_r']=corr(vc,fresh)
 out['groups'][label]['fresh_lists1_6']={'r':r6,'reliability':rel6,'corrected_r':r6/np.sqrt(rel6) if rel6>0 else None,'slope':float(np.dot(vc,six)/np.dot(vc,vc))}
 if 1000 in ids:
  base=hold[:,ids.index(1000)]
  out['groups'][label]['V_pick_vs_base_lists4_7']=stat(hold[idx,pick]-base)
  out['groups'][label]['oracle_vs_base_lists4_7']=stat(hold[idx,oracle]-base)
  mask=v<=v[:,ids.index(1000),None]+.05
  mask[mask.sum(axis=1)<2]=False
  def mc(x):
   means=(x*mask).sum(axis=1)/np.maximum(1,mask.sum(axis=1))
   return (x-means[:,None])[mask]
  cv,cy=mc(v),mc(y.mean(axis=2))
  if len(cv)>2 and np.dot(cv,cv)>1e-16 and np.dot(cy,cy)>1e-16:
   hr=corr(mc(y[:,:,:4].mean(axis=2)),mc(y[:,:,4:].mean(axis=2)));rr=2*hr/(1+hr);cr=corr(cv,cy)
   out['groups'][label]['competitive_within_005_V']={'n_cases':int(np.sum(mask.any(axis=1))),'n_entries':int(mask.sum()),'r':cr,'reliability':rr,'corrected_r':cr/np.sqrt(rr) if rr>0 else None,'slope':float(np.dot(cv,cy)/np.dot(cv,cv))}
for j in range(10):
 ids=[2000+j,3000+j,4000+j,5000+j]
 if not all(c in data for c in ids):continue
 ss=sorted(set.intersection(*(set(data[x]) for x in ids)));f,r,pr,pf=[np.array([data[c][s][1:].mean() for s in ss]) for c in ids]
 vf,vr,vpr,vpf=[np.array([values[c][s] for s in ss]) for c in ids]
 out['finishing'][j]={'before_delta':stat(r-pr),'after_delta':stat(f-pf),'finish_gain':stat(f-r),'before_better_fraction':float(np.mean(r<pr)),'after_better_fraction':float(np.mean(f<pf)),'V_before_better_fraction':float(np.mean(vr<vpr)),'V_after_better_fraction':float(np.mean(vf<vpf))}
 keep=np.array([not failures[2000+j][s] for s in ss])
 if keep.any():
  out['finishing'][j]['successful_repairs_only']={'n':int(keep.sum()),'before_delta':stat((r-pr)[keep]),'after_delta':stat((f-pf)[keep]),'before_better_fraction':float(np.mean((r<pr)[keep])),'after_better_fraction':float(np.mean((f<pf)[keep]))}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
