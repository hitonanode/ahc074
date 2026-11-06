"""列ごとの実際の fix を列の特徴量から学習し、設計ごとの合計が、設計の良し悪し（注文列 4 本の平均の差）を
model_hole / model_cost より当てるかを調べる。A = SOTA の設計、B = 窓 0 の設計（同じ seed）。"""
import pandas as pd, numpy as np, json
from sklearn.ensemble import HistGradientBoostingRegressor
SPC = str(__import__('pathlib').Path(__file__).resolve().parent) + '/'
RUNS = '/home/sato/ahc074/runs/'
def prep(f):
    d = pd.read_csv(SPC + f)
    d['last'] = (d.c == d.H - 1).astype(int); d['rel'] = d.c / (d.H - 1)
    d['dem'] = d.x + d.y; d['dmin'] = np.minimum(d.x, d.y) / d.dem.clip(lower=1)
    d['minority'] = np.minimum(d.n1, d.nc - d.n1)
    d['bal'] = d.x * d.y / d.dem.clip(lower=1)
    return d
A = prep('sota_cols_all.csv'); B = prep('w0_cols_all.csv')
F = ['x', 'y', 'reset', 'nc', 'nt', 'n1', 'minority', 'c', 'rel', 'last', 'dem', 'dmin', 'bal', 'deep0', 'deep1']
train = pd.concat([A[A.seed < 1000], B[B.seed < 1000]])
m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40, random_state=1)
m.fit(train[F], train.fix)
for d in (A, B): d['pred'] = m.predict(d[F])
test = pd.concat([A[A.seed >= 1000], B[B.seed >= 1000]])
print('per column (test seeds 1000-1999): corr(real fix, model hcost) %.3f, corr(real fix, learned) %.3f' % (
    np.corrcoef(test.fix, test.hcost)[0, 1], np.corrcoef(test.fix, test.pred)[0, 1]))
# design level
def design(d):
    g = d.groupby('seed')
    return pd.DataFrame({'fix': g.fix.sum(), 'pred': g.pred.sum(), 'hole': g.hcost.sum(), 'dig': g.dig.sum()})
DA, DB = design(A), design(B)
def scores(run):
    r = json.load(open(RUNS + run + '/result.json'))
    return pd.Series({int(c['seed']): np.mean(c['order_scores']) / 1024 for c in r['cases']})
TA = scores('20261107-011002_argon-des-perf-latew105'); TB = scores('20261107-011654_argon-cap-window0')
import re
def model_cost(run, seeds):
    out = {}
    for s in seeds:
        t = open(f'{RUNS}{run}/err/{s:04d}.txt').read()
        out[s] = float(re.search(r'^model_cost = ([-0-9.e+]+)', t, re.M).group(1))
    return pd.Series(out)
seeds = [s for s in DA.index if s in DB.index and s >= 1000]
MA = model_cost('20261107-011002_argon-des-perf-latew105', seeds); MB = model_cost('20261107-011654_argon-cap-window0', seeds)
D = pd.DataFrame({'dT': TA[seeds] - TB[seeds], 'dfix': DA.fix[seeds] - DB.fix[seeds], 'dpred': DA.pred[seeds] - DB.pred[seeds],
                  'dhole': DA.hole[seeds] - DB.hole[seeds], 'dmodel': MA - MB, 'ddig': DA.dig[seeds] - DB.dig[seeds]})
print('\ndesign level, test seeds 1000-1999 (A - B; real values are 4-sequence means):')
for k in ['dpred', 'dhole', 'dmodel']:
    print(f'  corr({k}, real fix diff) {np.corrcoef(D[k], D.dfix)[0, 1]:+.3f}   corr({k}, real total diff) {np.corrcoef(D[k], D.dT)[0, 1]:+.3f}')
print(f'  corr(real fix diff, real total diff) {np.corrcoef(D.dfix, D.dT)[0, 1]:+.3f}')
# combined: model_cost minus its hole part plus the learned fix
D['dcomb'] = D.dmodel - D.dhole / 1.0 * 0 + 0  # placeholder
X = np.column_stack([D.dmodel, D.dpred, D.dhole]); y = D.dT.values
coef, *_ = np.linalg.lstsq(np.column_stack([X, np.ones(len(y))]), y, rcond=None)
pred = np.column_stack([X, np.ones(len(y))]) @ coef
print('  linear fit of the total diff on (dmodel, dpred, dhole): coef', np.round(coef, 3), ' corr', round(np.corrcoef(pred, y)[0, 1], 3))
