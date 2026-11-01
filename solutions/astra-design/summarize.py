#!/usr/bin/env python3
"""保存したケース別データからlog比・標準誤差を再計算する。引数なしで比較名一覧。"""
import argparse, csv, gzip, math, pathlib, statistics

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('label', nargs='?')
p.add_argument('--metric', choices=['anneal_cost', 'sim_moves', 'total_moves', 'anneal_iters'])
a = p.parse_args()
h = pathlib.Path(__file__).resolve().parent
with gzip.open(h / 'experiments.csv.gz', 'rt') as f:
    rows = list(csv.DictReader(f))
if not a.label:
    for label in dict.fromkeys(r['label'] for r in rows):
        rr = [r for r in rows if r['label'] == label]
        print(label, rr[0]['mode'], len(rr), 'rows')
    raise SystemExit()
rows = [r for r in rows if r['label'] == a.label]
if not rows:
    p.error('不明な比較名')
metric = a.metric or ('sim_moves' if rows[0]['mode'] == 'sim' else 'anneal_cost')
baseline = {r['seed']: r for r in rows if r['binary'].startswith('base-')}
if not baseline:
    p.error('基準との比較がない記録です')
for name in sorted({r['binary'] for r in rows if not r['binary'].startswith('base-')}):
    pairs = [(float(r[metric]), float(baseline[r['seed']][metric]))
             for r in rows if r['binary'] == name and r[metric]]
    if not pairs:
        continue
    values = [100 * math.log(x / y) for x, y in pairs]
    mu = statistics.mean(values)
    se = statistics.stdev(values) / math.sqrt(len(values))
    w, t, l = [sum(fn(x, y) for x, y in pairs)
               for fn in [lambda x, y: x < y, lambda x, y: x == y, lambda x, y: x > y]]
    print(f'{name}: n={len(pairs)} {mu:+.6f} ± {se:.6f}% {w}/{t}/{l}')
