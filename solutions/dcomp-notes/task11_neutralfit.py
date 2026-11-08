"""Fit a cheap ranking of candidates by the measured result after repair (flock+nice)."""
from pathlib import Path
import json,re,math
import numpy as np
from sklearn.linear_model import Ridge
N=Path(__file__).resolve().parent;ROOT=N.parents[1];R=Path('/home/sato/ahc074/runs')
ids=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(N/'t11-neutraltrain.log').read_text(),re.M);assert len(ids)==1
run=ids[0];assert json.loads((R/run/'meta.json').read_text())['status']=='ok'
cases=json.loads((R/run/'result.json').read_text())['cases'];assert sorted(int(c['seed'])for c in cases)==list(range(200)) and all(c['score']>0 for c in cases)
groups={}
for seed in range(200):
 for line in (R/run/'err'/f'{seed:04d}.txt').read_text().splitlines():
  if not line.startswith('#heavycand '):continue
  z=line.split();assert len(z)==18,len(z)
  q,round_,rank=int(z[1]),int(z[2]),int(z[4]);op=z[3]
  x=np.array([float(z[6]),float(z[8]),float(z[16]),float(z[7]),float(op=='22'),float(op=='11')])
  y=-float(z[14]);floor=float(z[17])
  groups.setdefault((seed,q,round_),[]).append((rank,x,y,floor))
X=[];Y=[];W=[]
for (seed,q,round_),rows in groups.items():
 rows.sort();assert [r[0]for r in rows]==list(range(1,len(rows)+1))
 if seed>=100 or len(rows)<2:continue
 x=np.array([r[1]for r in rows]);y=np.array([r[2]for r in rows]);x-=x.mean(axis=0);y-=y.mean()
 X.extend(x);Y.extend(y);W.extend([1/len(rows)]*len(rows))
X=np.array(X);Y=np.array(Y);W=np.array(W);scale=np.sqrt(np.average(X**2,axis=0,weights=W));scale[scale<1e-8]=1
prior=np.array([0.,0.,0.,1.,0.,0.])
def stats(z):return {'mean':float(z.mean()),'se':float(z.std(ddof=1)/math.sqrt(len(z))),'n':len(z)}
def evaluate(coef,lo,hi,first_only=True,oracle=False):
 delta=np.zeros(hi-lo);queries=0;changed=0
 for (seed,q,round_),rows in groups.items():
  if not lo<=seed<hi or (first_only and round_!=1):continue
  x=np.array([r[1]for r in rows]);y=np.array([r[2]for r in rows]);floor=rows[0][3];width=min(6,len(y))
  assert all(r[3]==floor for r in rows)
  old=min(floor,float(y[:width].min()))
  selected=np.arange(len(y))if oracle else np.argsort(x@coef,kind='stable')[:width]
  new=min(floor,float(y[selected].min()))
  delta[seed-lo]+=(new-old)/1024;queries+=1;changed+=new!=old
 return {'moves_proxy':stats(delta),'queries':queries,'changed_minimum':changed}
models=[]
for alpha in [.1,1.,10.,100.]:
 fit=Ridge(alpha=alpha,fit_intercept=False).fit(X/scale,Y-X@prior,sample_weight=W)
 coef=prior+fit.coef_/scale
 models.append({'alpha':alpha,'coef':coef.tolist(),'train':evaluate(coef,0,100),'validation':evaluate(coef,100,200)})
best=min(models,key=lambda m:m['validation']['moves_proxy']['mean']);v=best['validation']['moves_proxy'];gate=v['mean']+2*v['se']<0
out={'run':run,'features':['path_size','repeats','hides','raw_value_gap','origin22','origin11'],'fit_rows':len(X),'groups':len(groups),'models':models,'best_alpha':best['alpha'],'gate_2se':gate,'oracle_validation':evaluate(prior,100,200,oracle=True)}
(N/'t11-neutralfit.json').write_text(json.dumps(out,indent=2)+'\n')
print('rows/groups',len(X),len(groups),'oracle',out['oracle_validation'])
for m in models:print(m)
print('gate',gate)
if gate:
 s=(ROOT/'solutions/dcomp-combo-alt1/main.cpp').read_text();coef=best['coef']
 begin=s.index('                    std::sort(neutral_candidates.begin(), neutral_candidates.end(),')
 pos=s.index('                                  if (cfg.candidate_priority) {',begin)
 end=pos+len('                                  if (cfg.candidate_priority) {')
 expression='+'.join(f'({coef[i]:.17g})*{term}'for i,term in enumerate(['c.path.size()','c.repeats','c.hides','c.value','(c.origin==1)','(c.origin==2)']))
 add='''
                                      static const bool linear=SearchConfig::get("NEUTRAL_LINEAR",1);
                                      if(linear) {
                                          auto rank=[](const auto& c){return '''+expression+''';};
                                          const double av=rank(a),bv=rank(b);
                                          if(av!=bv)return av<bv;
                                      }'''
 s=s[:end]+add+s[end:]
 d=ROOT/'solutions/dcomp-t11-neutral-linear';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n中立候補の6枠を、修復前の辞書式priorityに代わり修復後の費用の線形予測で選ぶ。特徴は既に保存している手数、重複数、隠れる紙数、費用、1→1/2→2の種別。一次式なので状態走査や修復を増やさない。同じ予測値なら従来のpriorityで決める。F3_NEUTRAL_LINEAR=0で従来規則に戻せる。\n\n教師は24枠で実際に修復したrun '+run+'。seed0–99でquery内中心化ridge、100–199で正則化を選んだ。offlineの値はplan_cost上の条件付き利得なので、実際のスコア改善はreplayで確認する。予算は両コンパイラ共通、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
