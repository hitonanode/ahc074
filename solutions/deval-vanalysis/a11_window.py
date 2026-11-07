"""窓の割り当てを変えた設計（全部やり直し）と、焼きなまし以降だけ変えた設計の中で、V16 で選ぶ得（restart7、検証 seed 500-999、列 1-7 で測る）。
設計 0: base、1-3: 全部やり直し（窓の割り当てから）、4-6: 焼きなまし以降だけやり直し。"""
import json, itertools
import numpy as np
from vlib import *
r7 = load('restart7')
X, Y = r7['X'][500:], r7['Y'][500:]
V = json.load(open(HERE.parent / 'deval-vbranch-o3/V.json'))
pred = X @ np.array(V['coefficients']) + V['intercept']
y17 = Y[:, :, 1:].mean(2)              # 列 1-7（base の元の列の運を除く）
mean = y17.mean()
n = len(y17)
def gain(sets):
    """各ケースで sets の設計から V で選び、その集合の平均（ランダムに選んだ場合）と比べた得、base との差。"""
    out_r, out_b = [], []
    for s in sets:
        s = list(s); p = pred[:, s].argmin(1)
        got = y17[np.arange(n), np.array(s)[p]]
        out_r.append((got - y17[:, s].mean(1)) / mean * 100)
        out_b.append((got - y17[:, 0]) / mean * 100)
    r = np.mean(out_r, 0); b = np.mean(out_b, 0)
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
    return f'vs random {r.mean():+.3f}±{se(r):.3f}%   vs base {b.mean():+.3f}±{se(b):.3f}%'
print('pairs base+full     ', gain([(0, i) for i in (1, 2, 3)]))
print('pairs base+anneal   ', gain([(0, i) for i in (4, 5, 6)]))
print('pairs full+full     ', gain(list(itertools.combinations((1, 2, 3), 2))))
print('pairs anneal+anneal ', gain(list(itertools.combinations((4, 5, 6), 2))))
print('4: base+3 full      ', gain([(0, 1, 2, 3)]))
print('4: base+3 anneal    ', gain([(0, 4, 5, 6)]))
print('7: all              ', gain([(0, 1, 2, 3, 4, 5, 6)]))
# 真の良し悪しのばらつき（注文列 7 本の平均の、列の雑音を除いた分散）
def true_sd(s):
    Ys = Y[:, s, 1:]; m = Ys.mean(2); dev = m - m.mean(1, keepdims=True)
    noise = Ys.var(2, ddof=1).mean() / Ys.shape[2]
    k = len(s); tv = (dev ** 2).sum(1).mean() / (k - 1) - noise
    return np.sqrt(max(tv, 0)) / mean * 100
print(f'true SD: full restarts {true_sd([1,2,3]):.3f}%  anneal restarts {true_sd([4,5,6]):.3f}%  (moves/order relative)')
