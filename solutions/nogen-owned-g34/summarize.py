"""保存された評価結果の集計。解法もテスターも実行しない。"""
import json, math, statistics, sys
from pathlib import Path
ROOT = Path('/home/sato/ahc074/runs')
REF = '20261106-085703_argon-des-perf-latew105'
def scores(run):
    return {str(c['seed']): c['score'] for c in json.loads((ROOT/run/'result.json').read_text())['cases']}
def compare(a,b):
    common=[k for k in a.keys() & b.keys() if a[k]>0 and b[k]>0]
    d=[100*math.log(a[k]/b[k]) for k in common]
    return dict(n=len(d), log_pct=statistics.mean(d), se_pct=statistics.stdev(d)/math.sqrt(len(d)) if len(d)>1 else 0, WTL=[sum(a[k]<b[k] for k in common),sum(a[k]==b[k] for k in common),sum(a[k]>b[k] for k in common)])
def quantile(a,p):
    a=sorted(a);x=(len(a)-1)*p;i=int(x)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
ref=scores(REF)
for run in sys.argv[1:]:
    cases=json.loads((ROOT/run/'metrics.json').read_text())['cases']
    sc=scores(run); valid=[x for x in sc.values() if x>0]
    ms=[c['stderr'] for c in cases.values() if c['score']>0]
    judge=[m['end_sec']+.04*m['helper_end_sec']+.35*m['req_sec'] for m in ms]
    print(run, 'mean',statistics.mean(valid),'WA',len(sc)-len(valid),'vs_sota',compare(sc,ref))
    print('judge',dict(mean=statistics.mean(judge),p99=quantile(judge,.99),max=max(judge),over2=sum(x>2 for x in judge)))
    keys=['control_map_sec','control_design_sec','helper_end_sec','req_sec','end_sec','ng_base_sec','ng_helper_sec','ng_alternate_sec','pc_model_col','pc_model_hole','pc_model_gc','control_map_before','control_map_after','joint_helper_trials','joint_helper_wins','product_helper_trials','product_helper_wins','alternate_trials','alternate_wins','alternate_immediate_saved','plan_failures','self_wrong','audit_owner_violations','audit_unowned_papers','ng_class0_sec','ng_class1_sec','ng_class2_sec']
    keys += sorted({k for m in ms for k in m if k.startswith('cfprof_') and k.endswith('_exc')})
    print('metrics', {k:statistics.mean(m[k] for m in ms if k in m) for k in keys if any(k in m for m in ms)})
    print('classes',{f'class{i}':dict(orders=statistics.mean(m[f'class{i}_orders'] for m in ms), moves_per_order=sum(m[f'class{i}_moves'] for m in ms)/sum(m[f'class{i}_orders'] for m in ms)) for i in range(3) if all(f'class{i}_orders' in m for m in ms)})
    for other in sys.argv[1:]:
        if other!=run: print('vs',other,compare(sc,scores(other)))
