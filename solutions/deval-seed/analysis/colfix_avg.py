"""colfix.py の列ごとの実際の手（fix, dig）を、--orders の全注文列で平均して、複数の設計を並べる。
使い方: python3 colfix_avg.py SEED RUN1 RUN2 ...（--design-from --orders の run）"""
import sys, json, collections
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import colfix
from pathlib import Path
ROOT = Path('/home/sato/ahc074/runs')
seed = int(sys.argv[1]); runs = sys.argv[2:]
res = {}
for r in runs:
    d = json.load(open(ROOT / r / 'result.json'))
    n = len(next(c for c in d['cases'] if int(c['seed']) == seed)['order_scores'])
    acc = None
    for j in range(n):
        a = colfix.analyze(r, seed, j, verbose=False)
        if acc is None: acc = a; acc['fix'] = list(a['fix']); acc['dig'] = list(a['dig'])
        else:
            acc['fix'] = [x + y for x, y in zip(acc['fix'], a['fix'])]; acc['dig'] = [x + y for x, y in zip(acc['dig'], a['dig'])]
    acc['fix'] = [x / n for x in acc['fix']]; acc['dig'] = [x / n for x in acc['dig']]
    acc['n'] = n
    res[r] = acc
for r, a in res.items():
    H = a['H']
    print(f'== {r} seed {seed}: H={H}, {a["n"]} sequences; fix {sum(a["fix"]):.3f} (model {sum(a["hcost"]):.3f}), dig {sum(a["dig"]):.3f} (model {sum(a["colcost"]):.3f}) moves/order')
    print('   c units tgts ones/units  demand(white,black)  hcost   fix   | colcost  dig')
    for c in range(H):
        print(f'  {c:2d} {a["nc"][c]:4d} {a["nt"][c]:4d}   {a["n1"][c]:2d}/{a["nc"][c]:<2d}        {a["hn"][c][0]:4d},{a["hn"][c][1]:<4d}     {a["hcost"][c]:.3f}  {a["fix"][c]:.3f} |  {a["colcost"][c]:.3f}  {a["dig"][c]:.3f}')
