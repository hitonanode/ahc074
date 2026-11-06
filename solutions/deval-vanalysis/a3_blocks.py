"""V16 のまとまりごとの寄与（係数はそのまま）と、まとまりを外した・残した再学習（学習 0-499、検証 500-999）。"""
import json
import numpy as np
from vlib import *
d = load('restart7'); X, Y, names = d['X'], d['Y'], list(d['names'])
V = json.load(open(HERE.parent / 'deval-vbranch-o3/V.json')); coef = np.array(V['coefficients'])
B = blocks(names)
te = slice(500, 1000); tr = slice(0, 500)
y = center(Y[te].mean(2))
v = center(X[te] @ coef)
print('within-case SD (moves/order): V %.4f  y(8-list mean) %.4f  cov(V,y) %.6f' % (v.std(), y.std(), (v * y).mean()))
print(f"{'block':6s} {'n':>3s} {'SD':>8s} {'cov(.,V)/var V':>15s} {'cov(.,y)/cov(V,y)':>18s} {'r(.,y)':>8s}")
for b, ids in B.items():
    p = center(X[te][:, :, ids] @ coef[ids])
    print(f"{b:6s} {len(ids):3d} {p.std():8.4f} {(p*v).mean()/(v*v).mean():15.3f} {(p*y).mean()/(v*y).mean():18.3f} {within_r(p, Y[te].mean(2)) if p.std()>0 else 0:8.3f}")
print()
def run(ids, label):
    c, b0 = fit(X[tr][:, :, ids], Y[tr].mean(2), 10.0)
    pred = X[te][:, :, ids] @ c + b0
    m = metrics(pred, Y[te]); ma = metrics(pred[:, GROUPS['anneal']], Y[te][:, GROUPS['anneal']])
    print(f"{label:28s} n={len(ids):3d}  all: {fmt(m)}   anneal-only: r={ma['r']:.4f} vs base {ma['base']:+.3f}%")
allids = [i for b, ids in B.items() if b != 'CONST' for i in ids]
run(allids, 'all (V16 refit)')
for b in ['COL', 'GEN', 'HS', 'DP0', 'DP1', 'DP2']:
    run([i for i in allids if i not in B[b]], f'without {b}')
for keep in [['COL', 'GEN'], ['COL', 'GEN', 'HS'], ['COL', 'GEN', 'DP0'], ['COL', 'GEN', 'DP2'], ['COL', 'GEN', 'DP0', 'DP1', 'DP2'], ['COL', 'GEN', 'HS', 'DP0'], ['COL', 'GEN', 'HS', 'DP2']]:
    run([i for b in keep for i in B[b]], 'only ' + '+'.join(keep))
