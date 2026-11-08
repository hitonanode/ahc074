#!/usr/bin/env python3
"""Per-case means (with standard errors over seeds) of analyze.py's results.

usage: summarize.py RESULTS.json
"""
import json
import sys
from collections import Counter, defaultdict

import numpy as np


def ms(values):
    v = np.asarray(values, dtype=float)
    return f'{v.mean():.3f} ± {v.std(ddof=1) / len(v) ** .5:.3f}' if len(v) > 1 else f'{v.mean():.3f}'


def main():
    res = json.load(open(sys.argv[1]))
    n = len(res)
    print(f'{n} cases (seeds {res[0]["seed"]}..{res[-1]["seed"]})')
    print('G windows', ms([r['G'] for r in res]))
    print('near pairs', ms([r['near_pairs'] for r in res]), ' compatible', ms([r['compatible'] for r in res]))
    classes = sorted({k for r in res for k in r['by_err']})
    for c in classes:
        print(f'  incompatible, errors (min-max side) {c}: pairs {ms([r["by_err"].get(c, 0) for r in res])}, '
              f'rescuable {ms([r["rescuable_by_err"].get(c, 0) for r in res])}')
    print('rescuable pairs', ms([r['rescuable'] for r in res]))
    cps = [c for r in res for c in r['cands_per_side']]
    print('candidates per side of rescuable pairs: mean', f'{np.mean(cps):.3f}', Counter(min(c, 5) for c in cps))
    print('moves (labels) per request:')
    labels = sorted({k for r in res for k in r['label_per_request']})
    for l in labels:
        print(f'  {l:8s} {ms([r["label_per_request"].get(l, 0) for r in res])}')
    print('papers moved per request', ms([r['moved_papers_per_request'] for r in res]),
          ' visible at the start', ms([r['visible_at_start'] for r in res]))
    fate = Counter()
    for r in res:
        fate.update(r['prev_fate'])
    tot = sum(fate.values())
    print('previous request\'s paper in the next request:', {k: f'{v / tot:.3f}' for k, v in fate.most_common()})
    # uses
    uses_n = [len(r['uses']) for r in res]
    print('uses (requests of a side of a rescuable pair) per case', ms(uses_n))
    allu = [u for r in res for u in r['uses']]
    print('cost per use: optimistic (no clearing)', f'{np.mean([u["opt"] for u in allu]):.3f}',
          ' with clearing 0.96', f'{np.mean([u["real"] for u in allu]):.3f}')
    how = Counter(u['how'].split('+')[0] for u in allu)
    print('cheapest candidate is:', {k: f'{v / len(allu):.3f}' for k, v in how.most_common()})
    print('  the previous request\'s paper:', f'{sum("+prev" in u["how"] for u in allu) / len(allu):.4f}')
    for key in ('opt', 'real'):
        for th in (0.5, 1.0, 1.5):
            per_case = []
            for r in res:
                pp = defaultdict(list)
                for u in r['uses']:
                    pp[u['pair']].append(u[key])
                per_case.append(sum(1 for v in pp.values() if np.mean(v) <= th))
            print(f'pairs per case with mean {key} cost <= {th}: {ms(per_case)}')
    # reliably moved papers
    rel = [x for r in res for x in r['reliable']]
    sh = np.array([x['share'] for x in rel])
    print(f'products with >= 3 requests: {len(rel) / n:.1f} per case; the paper moved most often in their requests: '
          f'mean share {sh.mean():.3f}, share 1: {np.mean(sh >= .999):.3f}, >= 0.8: {np.mean(sh >= .8):.3f}')
    lab = Counter()
    for x in rel:
        if x['share'] >= .999:
            lab.update(x['labels'])
    t = sum(lab.values())
    print('  labels of those moved in every request:', {k: f'{v / t:.3f}' for k, v in lab.most_common(6)},
          ' same column:', f'{np.mean([x["same_col"] for x in rel if x["share"] >= .999]):.3f}')
    if 'onewindow_sides' in res[0]:
        print('print co-design of 1-window pairs (holes added to the repair paper on generic windows, its own '
              'targets still displayable by the comparator; per case):')
        print('  1-window sides', ms([r['onewindow_sides'] for r in res]))
        for h in (0, 1, 2, 3, 99):
            print(f'  holes <= {h}: sides {ms([r[f"codesign_sides_h{h}"] for r in res])}, '
                  f'pairs with both sides (distinct papers) {ms([r[f"codesign_pairs_h{h}"] for r in res])}')
    v = np.array([r['validate'] for r in res]).sum(0)
    print(f'legal exposure replays: {v[1]} of {v[0]} legal')


if __name__ == '__main__':
    main()
