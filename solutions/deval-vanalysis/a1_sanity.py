"""V16 の再現の確認: 特徴量が Astra の学習データと一致するか、係数を同じ手順で再現できるか、検証 seed での成績。"""
import json
import numpy as np
from vlib import *
d = load('restart7'); X, Y, names = d['X'], d['Y'], list(d['names'])
ref = np.load(HERE.parent / 'deval-vselect/target_cv_qmc_16.npz')
print('features equal to Astra training data (seeds 0-499):', np.allclose(ref['X'], X[:500]), 'max abs diff', np.abs(ref['X'] - X[:500]).max())
print('Y equal:', np.allclose(ref['Y'], Y[:500]))
V = json.load(open(HERE.parent / 'deval-vbranch-o3/V.json'))
assert V['feature_names'] == names
coef, b = fit(X[:500], Y[:500].mean(2), 10.0)
print('refit on 0-499 vs V.json: max coef diff', np.abs(coef - np.array(V['coefficients'])).max(), 'intercept', b, V['intercept'])
pred = X @ np.array(V['coefficients']) + V['intercept']
te = slice(500, 1000)
for g, ids in GROUPS.items():
    print(f'test 500-999 {g:6s}', fmt(metrics(pred[te][:, ids], Y[te][:, ids])))
mc = d['B'][:, :, list(d['baseline_names']).index('model_cost')]
for g, ids in GROUPS.items():
    print(f'model_cost   {g:6s}', fmt(metrics(mc[te][:, ids], Y[te][:, ids])))
