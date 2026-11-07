"""Judge-time model from the esw-climb4 submission (31/50 TLE): judge = 1.04 * design + 1.35 * requests + other
(local stderr times, CLOCK_SCALE 1.1). Usage: judge_model.py RUN [RUN...]"""
import re, sys
from pathlib import Path
import numpy as np
for run in sys.argv[1:]:
    d = []
    for f in Path('/home/sato/ahc074/runs', run, 'err').glob('*.txt'):
        t = f.read_text()
        g = lambda k: float(re.findall(rf'^{k} = (\S+)$', t, re.M)[-1])
        d.append((g('helper_end_sec'), g('req_sec'), g('end_sec')))
    a = np.array(d)
    des, req, end = a[:, 0], a[:, 1], a[:, 2]
    judge = 1.04 * des + 1.35 * req + (end - des - req)
    print(f'{run}: n {len(a)}  design {des.mean():.3f}  req {req.mean():.3f}  end {end.mean():.3f}  '
          f'judge mean {judge.mean():.3f}  p99 {np.quantile(judge, .99):.3f}  max {judge.max():.3f}  P(>2.0) {np.mean(judge > 2.0):.3f}  P(>1.9) {np.mean(judge > 1.9):.3f}')
