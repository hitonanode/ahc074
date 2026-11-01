#!/usr/bin/env python3
"""Recompute reported comparisons from the committed CSVs (32 problem clusters)."""
import csv,json,math,statistics
from pathlib import Path
from scipy.stats import t
HERE=Path(__file__).resolve().parent

def rows(name):
    with open(HERE/'results'/name,newline='') as f:return [{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
def compare(data,a,b):
    groups={}
    for r in data:
        groups.setdefault(r['problem_seed'],[]).append((math.log(r[a]/r[b]),(r[a]-r[b])/1024))
    x=[statistics.mean(z[0] for z in v) for v in groups.values()]
    y=[statistics.mean(z[1] for z in v) for v in groups.values()]
    n=len(x);mean=statistics.mean(x);se=statistics.stdev(x)/math.sqrt(n);crit=t.ppf(.975,n-1)
    return dict(candidate=a,reference=b,clusters=n,streams=len(data),log_ratio_percent=100*mean,
                SE_percent=100*se,CI95_percent=[100*(mean-crit*se),100*(mean+crit*se)],
                moves_per_order_difference=statistics.mean(y),moves_SE=statistics.stdev(y)/math.sqrt(n),
                cluster_WDL=[sum(v<0 for v in x),sum(v==0 for v in x),sum(v>0 for v in x)])
def main():
    primary=rows('primary.csv');extra=rows('extra.csv');deep=rows('deep.csv');data=primary+extra
    names=['base.design','linear-selected.final','mixed-selected.final']
    comparisons=[compare(data,names[1],names[0]),compare(data,names[2],names[0]),compare(data,names[2],names[1])]
    for got,want in zip(comparisons,[-.3733683971168633,-.48904080194635974,-.11567240482949578]):
        assert abs(got['log_ratio_percent']-want)<1e-10
    result=dict(means={n:statistics.mean(r[n] for r in data) for n in names},precision=comparisons,
                primary={n:compare(primary,n,'base.design') for n in primary[0] if n not in ['seed','problem_seed']},
                deep={n:compare(deep,n,'base.design') for n in deep[0] if n not in ['seed','problem_seed']})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
