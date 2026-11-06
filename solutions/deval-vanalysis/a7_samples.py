"""積分点の数を減らした V3（4・8・16 点）の精度。restart7（seed 500-999 で検証）と branch4（4 分岐の中で選ぶ）。"""
import sys
import numpy as np
from vlib import *
from extract import features, names
sys.dont_write_bytecode = True
r7 = load('restart7'); b4 = load('branch4')
nm = list(r7['names']); ix = {n: i for i, n in enumerate(nm)}
MODEL = HERE.parent / 'deval-model'
import json
ORDER = ['base', 'DESIGN_SEED_1', 'DESIGN_SEED_2', 'DESIGN_SEED_3', 'DSEED_A_1', 'DSEED_A_2', 'DSEED_A_3']
d = [np.load(MODEL / 'data' / f'{v}.npz', allow_pickle=True) for v in ORDER]
paths7 = [p for s in range(1000) for p in (x['paths'][s] for x in d)]
sys.path.insert(0, str(MODEL)); from prepare import state_file
ex = {json.loads(l)['tag']: json.loads(l) for l in open(HERE.parent / 'deval-vselect/experiments.jsonl') if l.strip()}
pathsb = [state_file(ex[f'trainbranch{i}']['design'], s) for s in b4['seeds'] for i in range(4)]
import subprocess
def feats(paths, n):
    out = subprocess.run([str(HERE / 'features_v16'), str(n)], input=('\n'.join(map(str, paths)) + '\n').encode(), capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float64).reshape(len(paths), -1)
F = ['col', 'gc', 'm_s2_it2_cost']
ids = [ix[f] for f in F]
for n in [16, 8, 4, 2, 1]:
    X7 = r7['X'] if n == 16 else feats(paths7, n).reshape(1000, 7, -1)
    Xb = b4['X'] if n == 16 else feats(pathsb, n).reshape(len(b4['seeds']), 4, -1)
    c, b0 = fit(X7[:500][:, :, ids], r7['Y'][:500].mean(2), 1e-6)
    m = metrics(X7[500:][:, :, ids] @ c + b0, r7['Y'][500:])
    pb = Xb[:, :, ids] @ c + b0
    yb = b4['Y'].mean(2); pick = pb.argmin(1)
    g = (yb[np.arange(len(yb)), pick] - yb.mean(1)) / yb.mean() * 100
    print(f'samples {n:2d}: restart7 test r={m["r"]:.4f} base {m["base"]:+.3f}%   branch4 r={within_r(pb, yb):.4f} pick vs random {g.mean():+.3f}±{g.std(ddof=1)/np.sqrt(len(g)):.3f}%   coef ' + ' '.join(f'{x:+.3f}' for x in c))
