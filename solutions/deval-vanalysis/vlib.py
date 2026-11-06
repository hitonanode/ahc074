"""V の解析の共通部品: ケース内の中心化、ridge（Astra と同じ手順）、ケース内の相関と選択の得。"""
import os
for k in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ.setdefault(k, '1')
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
HERE = Path(__file__).resolve().parent
GROUPS = {'all': [0, 1, 2, 3, 4, 5, 6], 'full': [0, 1, 2, 3], 'anneal': [0, 4, 5, 6]}

def center(a):
    return a - a.mean(axis=1, keepdims=True)

def fit(X, y, alpha=10.0):
    """ケース内で中心化した特徴（ケース内の変動で標準化）に ridge。返り値は元の尺度の係数と切片。"""
    xc, yc = center(X), center(y)
    scale = np.sqrt(np.mean(xc ** 2, axis=(0, 1)))
    scale[scale < 1e-10] = 1
    m = Ridge(alpha=alpha, fit_intercept=False).fit((xc / scale).reshape(-1, X.shape[-1]), yc.ravel())
    coef = m.coef_ / scale
    return coef, float(y.mean() - X.mean(axis=(0, 1)) @ coef)

def within_r(pred, y):
    a, b = center(pred).ravel(), center(y).ravel()
    return float(a @ b / np.sqrt((a @ a) * (b @ b)))

def metrics(pred, Y):
    """pred: seeds x designs、Y: seeds x designs x 8 列。ケース内の相関（補正つき）と、pred で選んだときの得。"""
    y = Y.mean(axis=2)
    r = within_r(pred, y)
    h1, h2 = Y[:, :, :4].mean(2), Y[:, :, 4:].mean(2)
    rh = within_r(h1, h2)
    rel = 2 * rh / (1 + rh)
    n = len(y)
    pick = pred.argmin(axis=1)
    got = y[np.arange(n), pick]
    gain_base = (got - y[:, 0]) / y.mean() * 100
    gain_rand = (got - y.mean(1)) / y.mean() * 100
    # pred で選び、後半 4 列で測る / oracle は前半 4 列で選んで後半 4 列で測る
    g2 = h2[np.arange(n), pick]; o = h2[np.arange(n), h1.argmin(1)]
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
    return dict(r=r, r_corr=r / np.sqrt(rel), base=gain_base.mean(), base_se=se(gain_base),
                rand=gain_rand.mean(), rand_se=se(gain_rand),
                half_vs_rand=((g2 - h2.mean(1)) / y.mean() * 100).mean(),
                oracle_half_vs_rand=((o - h2.mean(1)) / y.mean() * 100).mean())

def fmt(m):
    return (f"r={m['r']:.4f} (corr {m['r_corr']:.4f})  vs base {m['base']:+.3f}±{m['base_se']:.3f}%  "
            f"vs random {m['rand']:+.3f}±{m['rand_se']:.3f}%")

def load(name='restart7'):
    d = np.load(HERE / f'{name}.npz', allow_pickle=True)
    return {k: d[k] for k in d.files}

def blocks(names):
    """特徴のまとまり。COL: 列の取り出し、GEN: 汎用紙、HS: 取っ手の静的な集計、DP0/DP1/DP2: 被覆 DP（初期分布、更新 1 回後、2 回後）。"""
    out = {}
    for i, n in enumerate(names):
        if n in ('col',) or n.startswith(('nc_', 'np_')): b = 'COL'
        elif n == 'gc' or n.startswith(('t_generic', 't_gen_')): b = 'GEN'
        elif n.startswith('f_s2'): b = 'DP0'
        elif n.startswith('m_s2_it1'): b = 'DP1'
        elif n.startswith('m_s2_it2'): b = 'DP2'
        elif n in ('G', 'H'): b = 'CONST'
        else: b = 'HS'
        out.setdefault(b, []).append(i)
    return out
