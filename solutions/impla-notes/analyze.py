"""保存済み run の対応のある差。実行は評価ロックの下で行う。"""
import argparse
import json
import math
from pathlib import Path
import re
import statistics as st

RUNS = Path('/home/sato/ahc074/runs')
KEYS = ['dv_best','gobj_after','map_end_sec','helper_end_sec','req_sec','end_sec',
        'dv_finish_sec','dv_anneal_sec','dv_eval_sec','anneal_iters','dv_chosen',
        'mono_columns','mono_candidate_count','mono_candidate_max','plan_failures','perf_branch_chosen','perf_full_candidates']
PATTERN = re.compile(r'^('+'|'.join(KEYS)+r') = ([\d.eE+\-]+)$', re.M)

def stats(a):
    return {'mean': st.mean(a), 'se': st.stdev(a)/math.sqrt(len(a)) if len(a)>1 else 0}

def p99(a):
    a=sorted(a); x=(len(a)-1)*0.99; i=int(x)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)

def load(run, end):
    path=RUNS/run
    data=json.loads((path/'result.json').read_text())
    cases={c['seed']:c for c in data['cases'] if end is None or c['seed']<end}
    metrics={}
    for seed in cases:
        p=path/'err'/f'{seed:04d}.txt'
        if not p.exists(): p=path/'err'/f'{seed}.txt'
        metrics[seed]={k:float(v) for k,v in PATTERN.findall(p.read_text())}
    meta=json.loads((path/'meta.json').read_text())
    return cases,metrics,meta

def compare(base, candidate, end=None):
    a,am,meta=load(base,end); b,bm,bmeta=load(candidate,end)
    seeds=sorted(a.keys()&b.keys())
    good=[s for s in seeds if a[s]['score']>0 and b[s]['score']>0]
    ratios=[]
    for s in good:
        av=a[s].get('order_scores',[a[s]['score']]); bv=b[s].get('order_scores',[b[s]['score']])
        ratios.append(st.mean(100*math.log(y/x) for x,y in zip(av,bv) if x>0 and y>0))
    out={'base':base,'candidate':candidate,'n':len(good),'wa':[len(seeds)-sum(a[s]['score']>0 for s in seeds),len(seeds)-sum(b[s]['score']>0 for s in seeds)],
         'score_pct':stats(ratios),'wtl':[sum(x<0 for x in ratios),sum(x==0 for x in ratios),sum(x>0 for x in ratios)],
         'outside_load':[meta.get('outside_load'),bmeta.get('outside_load')],
         'extensions':[meta.get('extensions',[]),bmeta.get('extensions',[])], 'metrics':{},'candidate_only_metrics':{}}
    for k in KEYS:
        ss=[s for s in good if k in am[s] and k in bm[s]]
        if not ss:
            values=[bm[s][k] for s in good if k in bm[s]]
            if values:out['candidate_only_metrics'][k]={'n':len(values),**stats(values),'p99':p99(values),'max':max(values),'nonzero':sum(v!=0 for v in values)}
            continue
        scale=1000 if k.endswith('_sec') else 1
        av=[am[s][k]*scale for s in ss]; bv=[bm[s][k]*scale for s in ss]
        out['metrics'][k]={'n':len(ss),'difference':stats([y-x for x,y in zip(av,bv)]),
            'base_mean':st.mean(av),'candidate_mean':st.mean(bv),'base_p99':p99(av),'candidate_p99':p99(bv)}
    t=out['metrics']
    design=t['helper_end_sec']['difference']['mean']; req=t['req_sec']['difference']['mean']
    # A time saving is a credit available to the final deadline-based design.
    out['time_charge_pct']=design*0.0003+req*0.00055
    out['net_improvement_pct']=-out['score_pct']['mean']-out['time_charge_pct']
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('base'); p.add_argument('candidates',nargs='+')
    p.add_argument('--end',type=int); p.add_argument('--out',type=Path)
    args=p.parse_args()
    out=[compare(args.base,c,args.end) for c in args.candidates]
    if args.out: args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    for x in out:
        print(x['candidate'], 'n',x['n'],'WA',x['wa'],'score',x['score_pct'],'W/T/L',x['wtl'])
        for k,v in x['metrics'].items():
            print(' ',k, 'delta',v['difference'],'means',v['base_mean'],v['candidate_mean'],'p99',v['base_p99'],v['candidate_p99'])
        print(' candidate only',x['candidate_only_metrics'])
        print(' charge',x['time_charge_pct'],'net improvement',x['net_improvement_pct'],'outside',x['outside_load'])
