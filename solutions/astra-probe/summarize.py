"""Aggregate saved probes. Differences are candidate minus its paired model baseline.
SE is over barcode seeds, NOT uncertainty of the model's physical assumptions.
"""
from pathlib import Path
import csv
import math
import statistics

HERE = Path(__file__).resolve().parent


def read(name):
    return list(csv.DictReader((HERE/name).open()))


def describe(xs):
    m=statistics.mean(xs)
    se=statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else 0
    return f'n={len(xs)}, delta={m:+.9f} +/- {se:.9f}, better/tie/worse={sum(x<0 for x in xs)}/{sum(x==0 for x in xs)}/{sum(x>0 for x in xs)}, delta/10.62036={100*m/10.62036:+.4f}%'


def paired(file, group, baseline, metric='model'):
    rows=read(file)
    base={r['seed']:float(r[metric]) for r in rows if group(r)==baseline}
    groups=sorted({group(r) for r in rows}-{baseline})
    print(file)
    for key in groups:
        xs=[float(r[metric])-base[r['seed']] for r in rows if group(r)==key]
        print(' ',key,describe(xs))


paired('decoder_0_8.csv',lambda r:r['decoder_cost'],'-1')
paired('escape_0_4.csv',lambda r:(r['kind'],r['q']),('bits','0'))
paired('patch_0_8.csv',lambda r:r['fee'],'0')
paired('sparse_0_4.csv',lambda r:r['proxy_boost'],'0','moves')
for name in ('helper_0_8.csv','anchor_0_8.csv'):
    rows=read(name)
    valid=[float(r['decoder']) for r in rows if math.isfinite(float(r['decoder']))]
    print(name, 'tested_edges=',len(rows),'both_feasible=',len(valid),
          'below_3.4=',sum(x<3.4 for x in valid))
print('matching_0_8.csv',describe([float(r['gap_per_request']) for r in read('matching_0_8.csv')]))

totals={}
for r in read('module3_workload.csv'):
    totals[r['variant']]=totals.get(r['variant'],0)+float(r['cost_per_global_query'])
print('module3_workload totals:',totals)
searched=[read(f'module_search_{b}.csv')[-1] for b in range(9)]
gain=sum(float(r['delta']) for r in searched)
print('module mask synthesis, pooled toy workload: delta=',gain,'fraction of 10.62036=',gain/10.62036)
print('Warning: the canonical-to-free delta is already matched by allowing one filler; it is not a new improvement.')
rs=read('geodesic_0_2000.csv')
print('Input-specific universal bound:',len(rs),'seeds, mean=',statistics.mean(float(r['distance_expected_lower']) for r in rs))
