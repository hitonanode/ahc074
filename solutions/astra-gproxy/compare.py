"""入力単位の対応あり比較。模型、模擬、テスターを区別して表示する。"""
import argparse
import json
import math
from pathlib import Path
import statistics as st

HERE=Path(__file__).resolve().parent
def read(name):
    return {(r['seed'],r['map_seed']):r for p in (HERE/'data'/name).glob('[0-9][0-9][0-9][0-9]-*.json')
            for r in [json.loads(p.read_text())] if 'model_cost' in r.get('stats',{})}
def avgse(v):
    return st.mean(v),st.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0
def main():
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidates',nargs='+');a=p.parse_args()
    base=read(a.base)
    for name in a.candidates:
        c=read(name);ks=sorted(base.keys()&c.keys())
        print(name,'n=',len(ks))
        for key in ['sim_moves','model_cost','model_col','model_hole','model_gc','map_end_sec','anneal_end_sec','search_exact_evals']:
            if any(key not in c[k]['stats'] or key not in base[k]['stats'] for k in ks):continue
            b=[base[k]['stats'][key] for k in ks];d=[c[k]['stats'][key]-base[k]['stats'][key] for k in ks]
            log=[100*math.log(c[k]['stats'][key]/base[k]['stats'][key]) for k in ks] if min(b)>0 else []
            print(f'  {key}: base={st.mean(b):.6f} delta={avgse(d)[0]:+.6f} ± {avgse(d)[1]:.6f}',
                  f'log={avgse(log)[0]:+.4f} ± {avgse(log)[1]:.4f}%' if log else '',
                  f'W/D/L={sum(x<0 for x in d)}/{sum(x==0 for x in d)}/{sum(x>0 for x in d)}')
        print('  sim_wrong=',sum(c[k]['stats'].get('sim_wrong',0) for k in ks))
if __name__=='__main__':main()
