"""Read same-state budget observations; never execute a solution/tester."""
from pathlib import Path
import argparse, json, re, statistics as st, sys
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('stamp')
p.add_argument('--end', type=int, default=200)
a = p.parse_args()
here = Path(__file__).parent
root = Path('/home/sato/ahc074/runs')
base = root / (a.stamp + '_argon-des-perf-latew105')
trial = root / (a.stamp + '_argon-req-budgetprobe')
rows = []
metrics = []
rx = re.compile(r'^(\w+) = ([-+\d.eE]+)$', re.M)
files = 0
for order in range(2):
    prefix = Path('.') if order == 0 else Path('orders') / str(order)
    for seed in range(a.end):
        rel = prefix / 'err' / f'{seed:04d}.txt'
        out = prefix / 'out' / rel.name
        s = (trial / rel).read_text()
        t = (base / rel).read_text()
        assert (trial / out).read_bytes() == (base / out).read_bytes(), str(out)
        norm = lambda q: [l for l in q.splitlines() if l.startswith(('@paper', '@ops'))]
        assert norm(s) == norm(t), str(rel)
        files += 1
        m = {k: float(v) for k, v in rx.findall(s)}
        assert all(m[f'budget_{j}_invalid'] == 0 for j in range(3))
        metrics.append(m)
        for l in s.splitlines():
            if l.startswith('#budget '):
                rows.append([seed, order] + list(map(float, l.split()[1:])))
data = np.asarray(rows, dtype=np.float64)
np.save(here / 'observations.npy', data)
names = ['seed', 'order', 'request', 'mode', 'raw', 'ordinary', 'holes', 'generic',
         'depth', 'fillers', 'alternatives', 'gap', 'first_gain', 'base_moves',
         'moves', 'gain', 'base_sec', 'sec', 'valid']
index = {s:i for i,s in enumerate(names)}
means = {k: st.mean(m[k] for m in metrics) for k in metrics[0] if k.startswith('budget_')}
(here / 'metrics.json').write_text(json.dumps(means, indent=2)+'\n')
print('identical stdout/paper/ops files', files, 'observations', len(data), flush=True)
print('means', means, flush=True)
for name, bounds in [('ordinary',[0,5,8,10,12,15,100]), ('raw',[0,8,10,12,14,17,100]),
                     ('holes',[0,1,2,3,4,5,10,64]), ('fillers',[0,1,2,3,4,20]),
                     ('depth',[0,1,2,3,4,5,10,100]), ('gap',[-1,0.01,0.2,0.5,1,2,100]),
                     ('first_gain',[-100,-1e-8,1e-8,0.1,0.5,1,100])]:
    print('\nfeature', name, flush=True)
    for lo, hi in zip(bounds, bounds[1:]):
        for mode in range(3):
            d = data[(data[:, index['mode']]==mode) &
                     (data[:, index[name]]>=lo) & (data[:, index[name]]<hi)]
            if not len(d): continue
            gain = d[:, index['gain']]
            dt = d[:, index['sec']] - d[:, index['base_sec']]
            print(f'{lo:g}..{hi:g} mode{mode}: n={len(d)} gain={gain.mean():.7f} '
                  f'dt={1e6*dt.mean():.3f}us gain/case={gain.sum()/(2*a.end):.4f} '
                  f'dt/case={dt.sum()/(2*a.end):.6f}s '
                  f'better/same/worse={sum(gain>1e-8)}/{sum(abs(gain)<=1e-8)}/{sum(gain< -1e-8)}', flush=True)
