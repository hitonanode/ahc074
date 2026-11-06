"""分岐 4 本（clean4 の各候補を強制、seed 0-499）での選択: V16 と、少ない特徴量の V（restart7 の seed 0-499 で学習）。"""
import json
import numpy as np
from vlib import *
r7 = load('restart7'); b4 = load('branch4')
names = list(r7['names']); ix = {n: i for i, n in enumerate(names)}
X7, Y7 = r7['X'][:500], r7['Y'][:500]
Xb, Yb = b4['X'], b4['Y']
V = json.load(open(HERE.parent / 'deval-vbranch-o3/V.json'))
def sel(pred, Y):
    y = Y.mean(2); n = len(y); pick = pred.argmin(1)
    g = (y[np.arange(n), pick] - y.mean(1)) / y.mean() * 100
    # perfect selector estimate is not computable per case; report oracle by lists 0-3 measured on 4-7
    h1, h2 = Y[:, :, :4].mean(2), Y[:, :, 4:].mean(2)
    gv = (h2[np.arange(n), pick] - h2.mean(1)) / y.mean() * 100
    go = (h2[np.arange(n), h1.argmin(1)] - h2.mean(1)) / y.mean() * 100
    return within_r(pred, y), g.mean(), g.std(ddof=1) / np.sqrt(n), gv.mean(), go.mean()
def show(label, pred):
    r, g, se, gv, go = sel(pred, Yb)
    print(f'{label:44s} within-branch r={r:.4f}  pick vs random {g:+.3f}±{se:.3f}%  (lists 4-7: pick {gv:+.3f}%, oracle by 0-3 {go:+.3f}%)')
show('V16 (deval-vbranch-o3)', Xb @ np.array(V['coefficients']) + V['intercept'])
D2 = 'm_s2_it2_'
for feats in [['col', 'gc', D2 + 'cost'], ['col', 'gc', D2 + 'fix', D2 + 'fill', D2 + 'fdig'],
              ['col', 'gc', 'm_s2_it1_cost'], ['col', 'gc', 'f_s2_p1.6_cost'], ['col', 'gc', 'h2_d0'],
              ['col', 'gc', D2 + 'cost', 'f_s2_p1.6_cost', 'm_s2_it1_length', 'unit_minor_p1', 'f_s2_p1.6_fix', 'm_s2_it1_fix2', D2 + 'tailfix']]:
    ids = [ix[f] for f in feats]
    c, b0 = fit(X7[:, :, ids], Y7.mean(2), 1e-6)
    show('+'.join(f.replace('m_s2_it2_', 'D2.').replace('m_s2_it1_', 'D1.').replace('f_s2_p1.6_', 'D0.') for f in feats)[:44], Xb[:, :, ids] @ c + b0)
mc = None
y = Yb.mean(2); dev = Yb - Yb.mean(1, keepdims=True)
m8 = dev.mean(2); noise = (dev - m8[:, :, None]).var(2, ddof=1).mean() * 4 / 3
tv = (m8 ** 2).sum(1).mean() / 3 - noise / 8
print(f'branch set: true within-set SD {np.sqrt(tv):.4f} moves/order; perfect selector ~ {-100*1.029*np.sqrt(tv)/y.mean():.3f}% vs random')
