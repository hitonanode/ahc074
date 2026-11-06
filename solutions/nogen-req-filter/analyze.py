"""保存結果のみ集計する。共有runs/.lockの下で実行する。"""
import json,math,statistics,sys
from pathlib import Path
root=Path('/home/sato/ahc074/runs')
def read(name):
    p=root/name
    return {c['seed']:c for c in json.loads((p/'result.json').read_text())['cases']}
def compare(a,b):
    common=a.keys()&b.keys()
    dif=[]
    for k in sorted(common):
        x=a[k].get('order_scores',[a[k]['score']]);y=b[k].get('order_scores',[b[k]['score']])
        if not min(x+y)>0:continue
        dif.append(statistics.mean(100*math.log(s/t) for s,t in zip(x,y)))
    return {'n':len(dif),'log_pct':statistics.mean(dif),'SE':statistics.stdev(dif)/math.sqrt(len(dif)) if len(dif)>1 else 0,'WTL':[sum(x<0 for x in dif),sum(x==0 for x in dif),sum(x>0 for x in dif)]}
base=read(sys.argv[1])
for name in sys.argv[1:]:
    cases=read(name);print(name,'mean',statistics.mean(c['score'] for c in cases.values()),'vs_first',compare(cases,base))
    mm=json.loads((root/name/'metrics.json').read_text())['cases']
    metrics=[c['stderr'] for c in mm.values()]
    keys={k for m in metrics for k in m if k.startswith(('study_','value_filler','complete_value','value_seed','audit_','perforation_','d2_','perf_'))}
    keys|={'helper_end_sec','req_sec','end_sec','self_wrong','light_requests','op_label_errors'}
    for k in sorted(keys):
        a=[m[k] for m in metrics if k in m]
        if a:print(k,'mean',statistics.mean(a),'SE',statistics.stdev(a)/math.sqrt(len(a)) if len(a)>1 else 0,'max',max(a),'n',len(a))
