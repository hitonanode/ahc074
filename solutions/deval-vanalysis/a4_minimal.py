"""少ない特徴量の V: 解釈できる小さな組と、学習 seed 内の 5 分割で選ぶ前向き選択。検証は seed 500-999。"""
import numpy as np
from vlib import *
d = load('restart7'); X, Y, names = d['X'], d['Y'], list(d['names'])
ix = {n: i for i, n in enumerate(names)}
tr, te = slice(0, 500), slice(500, 1000)
def show(feats, alpha=1e-6, label=None):
    ids = [ix[f] for f in feats]
    c, b0 = fit(X[tr][:, :, ids], Y[tr].mean(2), alpha)
    pred = X[te][:, :, ids] @ c + b0
    m = metrics(pred, Y[te]); ma = metrics(pred[:, GROUPS['anneal']], Y[te][:, GROUPS['anneal']])
    print(f"{label or '+'.join(feats)}\n    {fmt(m)}  anneal-only r={ma['r']:.4f} base {ma['base']:+.3f}%")
    print('    coef: ' + '  '.join(f'{f}={x:+.3f}' for f, x in zip(feats, c)))
    return m
D2 = 'm_s2_it2_'
show(['col', 'gc', D2 + 'cost'])
show(['col', 'gc', D2 + 'fix', D2 + 'fill', D2 + 'fdig'])
show(['col', 'gc', D2 + 'fix', D2 + 'fill', D2 + 'fdig', D2 + 'lastfix'])
show(['col', 'gc', D2 + 'raw', D2 + 'fix', D2 + 'fill', D2 + 'fdig', D2 + 'lastfix', D2 + 'tailfix'])
show(['col', 'gc', 't_generic_p2', D2 + 'raw', D2 + 'fix', D2 + 'fill', D2 + 'fdig', D2 + 'lastfix', D2 + 'tailfix'])
show(['col', 'gc', 'f_s2_p1.6_cost'], label='DP0 only: col+gc+f_s2_p1.6_cost')
show(['col', 'gc', 'f_s2_p1.6_fix', 'f_s2_p1.6_fill', 'f_s2_p1.6_fdig'], label='DP0 only: col+gc+fix+fill+fdig')
show(['col', 'gc', 'h2_d0'], label='static: col+gc+h2_d0 (= model_cost terms, refit)')
show(['col', 'gc', 'h2_d0', 'h2_balance', 'h2_last1'], label='static: col+gc+h2_d0+h2_balance+h2_last1')

# forward selection with 5-fold CV over seeds 0-499
live = [i for i in range(len(names)) if center(X[tr][:, :, i]).std() > 1e-12]
folds = np.arange(500) % 5
def cv_r(ids):
    pred = np.zeros((500, 7))
    for f in range(5):
        trn, val = folds != f, folds == f
        c, b0 = fit(X[:500][trn][:, :, ids], Y[:500][trn].mean(2), 1e-3)
        pred[val] = X[:500][val][:, :, ids] @ c + b0
    return within_r(pred, Y[:500].mean(2))
chosen = []
for step in range(15):
    best = max((cv_r(chosen + [i]), i) for i in live if i not in chosen)
    chosen.append(best[1])
    c, b0 = fit(X[tr][:, :, chosen], Y[tr].mean(2), 1e-3)
    m = metrics(X[te][:, :, chosen] @ c + b0, Y[te])
    print(f'forward {step+1:2d}: +{names[best[1]]:22s} cv r={best[0]:.4f}  test r={m["r"]:.4f} base {m["base"]:+.3f}%')
