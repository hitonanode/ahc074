"""Run only under flock+nice, after the 300-seed rollout run is complete."""
from pathlib import Path
import json,math,re
import numpy as np
from sklearn.linear_model import Ridge
R=Path('/home/sato/ahc074/runs');N=Path(__file__).resolve().parent;ROOT=N.parents[1]
reference,run=(N/'t11-tietrain-runs.txt').read_text().split()
meta=json.loads((R/run/'meta.json').read_text());assert meta['status']=='ok'
cases=json.loads((R/run/'result.json').read_text())['cases']
assert sorted(int(c['seed'])for c in cases)==list(range(300)) and all(c['score']>0 for c in cases)
parent=(ROOT/'solutions/dcomp-combo-alt1/main.cpp').read_text()
oldconst=float(re.search(r'kTieConst = ([-+0-9.eE]+)',parent).group(1))
oldcoef=np.array([float(x)for x in re.search(r'kTieCoef = \{([^}]+)\}',parent).group(1).split(',')])
scores={int(c['seed']):float(c['score'])for c in cases}
groups={};same=0
for seed in range(300):
 same+=(R/reference/'out'/f'{seed:04d}.txt').read_bytes()==(R/run/'out'/f'{seed:04d}.txt').read_bytes()
 for line in (R/run/'err'/f'{seed:04d}.txt').read_text().splitlines():
  if not line.startswith('#t11rf '):continue
  fields=line.split();q,i=map(int,fields[1:3]);data=np.array(list(map(float,fields[3:])))
  assert len(data)==12 and q%32==0
  groups.setdefault((seed,q),{})[i]=data
assert same==300
X=[];target=[];weights=[];seeds=[]
for (seed,q),group in groups.items():
 assert sorted(group)==list(range(len(group)))
 base=group[0]
 for i in range(1,len(group)):
  row=group[i];x=row[3:]-base[3:];g=row[1]-base[1];y=row[2]-base[2]
  X.append(x);target.append(y-g);weights.append(1/(len(group)-1));seeds.append(seed)
X=np.array(X);target=np.array(target);weights=np.array(weights);seeds=np.array(seeds)
fit=seeds<200
mean=np.average(X[fit],axis=0,weights=weights[fit]);std=np.sqrt(np.average((X[fit]-mean)**2,axis=0,weights=weights[fit]));std[std<1e-8]=1
def evaluate(intercept,coef,lo,hi):
 delta=np.zeros(hi-lo);changes=0;oldchoices=0;newchoices=0
 for (seed,q),group in groups.items():
  if not lo<=seed<hi:continue
  base=group[0];old_index=new_index=0;old_best=new_best=0.
  for i in range(1,len(group)):
   row=group[i];x=row[3:]-base[3:];g=row[1]-base[1]
   old=g+oldconst+x@oldcoef;new=g+intercept+x@coef
   if old<old_best:old_index=i;old_best=old
   if new<new_best:new_index=i;new_best=new
  delta[seed-lo]+=(group[new_index][2]-group[old_index][2])/32
  changes+=old_index!=new_index;oldchoices+=old_index!=0;newchoices+=new_index!=0
 pct=np.array([100*x/(scores[seed]/1024)for seed,x in zip(range(lo,hi),delta)])
 def stats(z):return {'mean':float(z.mean()),'se':float(z.std(ddof=1)/math.sqrt(len(z))),'n':len(z)}
 return {'moves':stats(delta),'pct_estimate':stats(pct),'changed':changes,'old_choices':oldchoices,'new_choices':newchoices}
models=[]
for alpha in [1.,10.,100.,1000.]:
 reg=Ridge(alpha=alpha).fit((X[fit]-mean)/std,target[fit]-oldconst-X[fit]@oldcoef,sample_weight=weights[fit])
 fullcoef=oldcoef+reg.coef_/std;fullconst=oldconst+reg.intercept_-mean@(reg.coef_/std)
 models.append({'alpha':alpha,'intercept':float(fullconst),'coefficients':fullcoef.tolist(),
                'train':evaluate(fullconst,fullcoef,0,200),'validation':evaluate(fullconst,fullcoef,200,300)})
best=min(models,key=lambda m:m['validation']['moves']['mean'])
estimate=best['validation']['moves'];gate=estimate['mean']+2*estimate['se']<0
out={'run':run,'reference':reference,'identity':same,'groups':len(groups),'rows':len(X),'old_const':oldconst,'old_coef':oldcoef.tolist(),'models':models,'best_alpha':best['alpha'],'gate_2se':gate}
(N/'t11-tiefit.json').write_text(json.dumps(out,indent=2)+'\n')
print('labels',len(X),'groups',len(groups),'identity',same)
for m in models:print('alpha',m['alpha'],'validation',m['validation'])
print('gate',gate)
if gate:
 for name,blend in [('dcomp-t11-tie-refit',1.),('dcomp-t11-tie-half',.5)]:
  coef=oldcoef+blend*(np.array(best['coefficients'])-oldcoef);intercept=oldconst+blend*(best['intercept']-oldconst)
  s=re.sub(r'kTieConst = [-+0-9.eE]+',f'kTieConst = {intercept:.17g}',parent)
  s=re.sub(r'kTieCoef = \{[^}]+\}', 'kTieCoef = {'+', '.join(f'{x:.17g}'for x in coef)+'}',s)
  d=ROOT/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
  (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n近接した完成計画の線形補正の係数だけを更新する。alt1の方策による40本×5注文の共通乱数ロールアウトを教師にし、seed0–199で従来係数をpriorとするridge回帰、200–299のラベルで正則化を選ぶ。元の9特徴とgap .3、候補・探索回数をそのまま使う。従来からの更新量は'+str(blend)+'倍。\n\n訓練run '+run+'。係数生成はtask11_tiefit.py。実replayで検証するまで改善とは扱わない。両コンパイラ共通係数・固定予算。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。時計分岐なし。\n')
