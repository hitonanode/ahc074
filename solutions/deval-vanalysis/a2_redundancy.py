"""特徴量の冗長さ: ケース内で変動しない特徴、ケース内で他と完全に一致する特徴。"""
import numpy as np
from vlib import *
d = load('restart7'); X, names = d['X'], list(d['names'])
xc = center(X).reshape(-1, X.shape[-1])
sd = xc.std(0)
print('constant within case:', [names[i] for i in np.where(sd < 1e-12)[0]])
live = np.where(sd >= 1e-12)[0]
C = np.corrcoef(xc[:, live].T)
seen = set()
for a in range(len(live)):
    dup = [names[live[b]] for b in range(a + 1, len(live)) if abs(C[a, b]) > 0.99999]
    if dup and names[live[a]] not in seen:
        print(f'{names[live[a]]:22s} == {dup}')
        seen.update(dup)
# rank of the within-case feature matrix
s = np.linalg.svd((xc[:, live] / sd[live]), compute_uv=False)
print('features', len(names), 'non-constant', len(live), 'numerical rank (sv > 1e-6 of max)', int((s > 1e-6 * s[0]).sum()))
print('effective dims for 99% / 99.9% of standardized within-case variance:',
      int(np.searchsorted(np.cumsum(s**2) / np.sum(s**2), .99) + 1), int(np.searchsorted(np.cumsum(s**2) / np.sum(s**2), .999) + 1))
