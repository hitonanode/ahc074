"""取っ手の項のどこが効くか: フィラーなしの不一致数（raw）と、被覆後の費用（cost）を、色分布の更新 0・1・2 回で比べる。"""
import numpy as np
from vlib import *
d = load('restart7'); X, Y, names = d['X'], d['Y'], list(d['names'])
ix = {n: i for i, n in enumerate(names)}
tr, te = slice(0, 500), slice(500, 1000)
def show(feats, label=None):
    ids = [ix[f] for f in feats]
    c, b0 = fit(X[tr][:, :, ids], Y[tr].mean(2), 1e-6)
    pred = X[te][:, :, ids] @ c + b0
    m = metrics(pred, Y[te]); ma = metrics(pred[:, GROUPS['anneal']], Y[te][:, GROUPS['anneal']])
    print(f"{label or '+'.join(feats):58s} r={m['r']:.4f} base {m['base']:+.3f}%  anneal r={ma['r']:.4f} base {ma['base']:+.3f}%   coef " + ' '.join(f'{x:+.2f}' for x in c))
for it, pre in [(0, 'f_s2_p1.6_'), (1, 'm_s2_it1_'), (2, 'm_s2_it2_')]:
    show(['col', 'gc', pre + 'raw'], f'updates {it}: col+gc+raw (mismatches, no fillers)')
    show(['col', 'gc', pre + 'cost'], f'updates {it}: col+gc+cost (with fillers)')
# how much does the column-top distribution change between updates: within-case variation of raw
for pre in ['f_s2_p1.6_', 'm_s2_it1_', 'm_s2_it2_']:
    for f in ['raw', 'cost', 'fix', 'fill', 'fdig']:
        v = X[:, :, ix[pre + f]]
        print(f'{pre+f:22s} mean {v.mean():.3f}  within-case SD {center(v).std():.4f}', end='   ')
    print()
# per-label: which actual moves does each part track (within-case r with the 8-list mean of each label)
L = d['L'].mean(2); ln = list(d['label_names'])
print('\nlabel mean moves/order and within-case SD:', ', '.join(f'{n} {L[:,:,j].mean():.3f}/{center(L[:,:,j]).std():.4f}' for j, n in enumerate(ln)))
for f in ['col', 'gc', 'm_s2_it2_raw', 'm_s2_it2_cost', 'm_s2_it2_fix', 'm_s2_it2_fill', 'm_s2_it2_fdig', 'f_s2_p1.6_raw']:
    print(f'{f:16s} ' + ' '.join(f'{n}={within_r(X[:, :, ix[f]], L[:, :, j]):+.2f}' for j, n in enumerate(ln) if center(L[:, :, j]).std() > 1e-4))
