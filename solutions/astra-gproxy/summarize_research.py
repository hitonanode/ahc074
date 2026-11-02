"""報告に使う標準誤差と、最終模型の内訳の回帰を保存する。"""
from pathlib import Path
import json
import numpy as np

HERE=Path(__file__).resolve().parent
a=np.genfromtxt(HERE/'data/researchsim/features.tsv',names=True,delimiter='\t')
seeds=a['seed'].astype(int)
unique=np.unique(seeds)
keys=['gobj','bias2','hdiff_sd','hd_sd','model_cost','model_col','model_hole','model_gc','sim_moves','kept_pairs']
X=np.column_stack([a[k] for k in keys]);Xc=X.copy()
for s in unique:Xc[seeds==s]-=Xc[seeds==s].mean(axis=0)
def avgse(v):return [float(np.mean(v)),float(np.std(v,ddof=1)/len(v)**.5)]
summary={}
summary['inputs']=len(unique);summary['designs']=len(a)
summary['mean_kept_pairs']=avgse([a['kept_pairs'][seeds==s].mean() for s in unique])
summary['mean_model_within_sd']=avgse([a['model_cost'][seeds==s].std(ddof=1) for s in unique])
summary['mean_sim_within_sd']=avgse([a['sim_moves'][seeds==s].std(ddof=1) for s in unique])

# Input-cluster bootstrap. Resample whole groups of 12, preserving within-input dependence.
rr=np.random.default_rng(57931)
groups=np.array([np.where(seeds==s)[0] for s in unique])
boots=groups[rr.integers(0,len(unique),size=(2000,len(unique)))].reshape(2000,-1)
ci=keys.index('model_cost');si=keys.index('sim_moves')
corrs=[np.corrcoef(Xc[b,ci],Xc[b,si])[0,1] for b in boots]
summary['centered_model_sim_corr']=[float(np.corrcoef(Xc[:,ci],Xc[:,si])[0,1]),float(np.std(corrs,ddof=1))]

names=['gobj','bias2','hdiff_sd'];tr=seeds<56
x=Xc[tr][:,[keys.index(k) for k in names]]
y=Xc[tr][:,[keys.index(k) for k in ['model_cost','model_col','model_hole','model_gc','sim_moves']]]
coef=np.linalg.lstsq(x,y,rcond=None)[0];res=y-x@coef;inv=np.linalg.inv(x.T@x)
regs={}
for j,k in enumerate(['model_cost','model_col','model_hole','model_gc','sim_moves']):
    meat=np.zeros((3,3))
    for s in np.unique(seeds[tr]):
        u=seeds[tr]==s;v=x[u].T@res[u,j];meat+=np.outer(v,v)
    se=np.sqrt(np.diag(inv@meat@inv)*32/31*383/381)
    regs[k]={f:[float(b),float(e)] for f,b,e in zip(names,coef[:,j],se)}
summary['train_ols_cluster_se']=regs

# Holdout performance and input-cluster bootstrap SE for the fitted ridge predictor.
scale=x.std(axis=0)
coef_r=np.linalg.solve((x/scale).T@(x/scale)+np.eye(3),(x/scale).T@y[:,0])/scale
x1=x[:,:1];s1=x1.std(axis=0)
coef_1=np.linalg.solve((x1/s1).T@(x1/s1)+np.eye(1),(x1/s1).T@y[:,0])/s1
te=seeds>=56;xt=Xc[te][:,:3];yt=Xc[te,ci]
groups_t=np.array([np.where(seeds[te]==s)[0] for s in unique[unique>=56]])
bb=groups_t[rr.integers(0,len(groups_t),size=(2000,len(groups_t)))].reshape(2000,-1)
summary['test_predictions']={}
for name,pred in [('gobj',xt[:,:1]@coef_1),('three',xt@coef_r)]:
    cs=[np.corrcoef(pred[i],yt[i])[0,1] for i in bb]
    rms=[np.sqrt(np.mean((pred[i]-yt[i])**2)) for i in bb]
    summary['test_predictions'][name]={'corr':[float(np.corrcoef(pred,yt)[0,1]),float(np.std(cs,ddof=1))],
        'rmse':[float(np.sqrt(np.mean((pred-yt)**2))),float(np.std(rms,ddof=1))]}

summary['selection']={}
for name,criterion in [('gobj',Xc[:,keys.index('gobj')]),('model',Xc[:,ci]),('sim',Xc[:,si])]:
    vals=[]
    for s in unique:
        mask=seeds==s;at=np.argmin(criterion[mask]);vals.append(Xc[mask][at,[ci,si]])
    summary['selection'][name]={'model':avgse(np.array(vals)[:,0]),'sim':avgse(np.array(vals)[:,1])}

text=json.dumps(summary,indent=2)
(HERE/'data/research-summary.json').write_text(text)
print(text)
