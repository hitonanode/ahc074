"""分岐 4 本で学習し直した V: 分岐の中で選ぶ得が、全部やり直した設計で学習した V16 より上がるか。
branch4（seed 0-499、clean4 の 4 候補を強制した replay）を seed で 5 分割し、学習していない seed での選択の得を測る。"""
import json
import numpy as np
from vlib import *
r7 = load('restart7'); b4 = load('branch4')
names = list(r7['names']); ix = {n: i for i, n in enumerate(names)}
Xb, Yb = b4['X'], b4['Y']; nb = len(Xb)
X7, Y7 = r7['X'], r7['Y']
V = json.load(open(HERE.parent / 'deval-vbranch-o3/V.json')); coef16 = np.array(V['coefficients'])
live = [i for i in range(len(names)) if center(X7[:, :, i]).std() > 1e-12]
def pick_gain(pred, Y):
    y = Y.mean(2); n = len(y); p = pred.argmin(1)
    g = (y[np.arange(n), p] - y.mean(1)) / y.mean() * 100
    return g.mean(), g.std(ddof=1) / np.sqrt(n), within_r(pred, y)
folds = np.arange(nb) % 5
def cv(feat_ids, alpha, use7=False, w7=1.0):
    pred = np.zeros((nb, 4))
    for f in range(5):
        tr, te = folds != f, folds == f
        Xtr, ytr = Xb[tr][:, :, feat_ids], Yb[tr].mean(2)
        if use7:  # add the restart designs of the same training seeds (seeds < 500 of restart7)
            s7 = np.array(b4['seeds'])[tr]
            X7tr, y7tr = X7[s7][:, :, feat_ids], Y7[s7].mean(2)
            # stack by padding designs: fit on both sets through centering separately
            xc = np.concatenate([center(Xtr).reshape(-1, len(feat_ids)), np.sqrt(w7) * center(X7tr).reshape(-1, len(feat_ids))])
            yc = np.concatenate([center(ytr).ravel(), np.sqrt(w7) * center(y7tr).ravel()])
            sc = np.sqrt((xc ** 2).mean(0)); sc[sc < 1e-10] = 1
            from sklearn.linear_model import Ridge
            m = Ridge(alpha=alpha, fit_intercept=False).fit(xc / sc, yc); c = m.coef_ / sc
        else:
            c, _ = fit(Xtr, ytr, alpha)
        pred[te] = Xb[te][:, :, feat_ids] @ c
    return pick_gain(pred, Yb)
g = pick_gain(Xb @ coef16, Yb); print(f'V16 (restart-trained)            pick vs random {g[0]:+.3f} ± {g[1]:.3f}%  within r {g[2]:.3f}')
for alpha in [1, 10, 100, 1000]:
    g = cv(live, alpha); print(f'branch-trained, all features, a={alpha:<5} pick {g[0]:+.3f} ± {g[1]:.3f}%  r {g[2]:.3f}')
for alpha in [10, 100]:
    g = cv(live, alpha, use7=True); print(f'branch+restart, all features, a={alpha:<4} pick {g[0]:+.3f} ± {g[1]:.3f}%  r {g[2]:.3f}')
small = [ix[f] for f in ['col', 'gc', 'm_s2_it2_fix', 'm_s2_it2_fill', 'm_s2_it2_fdig', 'm_s2_it2_raw', 'm_s2_it2_lastfix', 'm_s2_it2_tailfix', 'f_s2_p1.6_cost', 'm_s2_it1_cost']]
for alpha in [0.01, 1, 10]:
    g = cv(small, alpha); print(f'branch-trained, 10 features, a={alpha:<5} pick {g[0]:+.3f} ± {g[1]:.3f}%  r {g[2]:.3f}')
y = Yb.mean(2); dev = Yb - Yb.mean(1, keepdims=True); m8 = dev.mean(2); noise = (dev - m8[:, :, None]).var(2, ddof=1).mean() * 4 / 3
tv = (m8 ** 2).sum(1).mean() / 3 - noise / 8
print(f'perfect selector ~ {-100 * 1.029 * np.sqrt(tv) / y.mean():.3f}% vs random')
