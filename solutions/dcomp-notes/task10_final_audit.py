"""Verify completed run provenance and that DesignStore replay reproduces list 0.

Read-only checks of recorded files; run under the common flock and nice.
"""
from pathlib import Path
import hashlib
import json
import re

N = Path(__file__).resolve().parent
R = Path('/home/sato/ahc074/runs')
normal = json.loads((N/'t10-final-normal.json').read_text())
replay = json.loads((N/'t10-final-replay.json').read_text())
clang = json.loads((N/'t10-final-clang.json').read_text())
frozen = '8fae7ff4cbfa331797ef8f3f6835cf6ad912f04fa5a94f3fa084e11a563f97c6'
pairs = [(normal['runs'][2], replay['reference']),
         (normal['runs'][3], replay['candidate'])]
out = {'list0_identity': {}, 'runs': {}}
for a, b in pairs:
    different = []
    for seed in range(2000):
        paths = [R/rid/'out'/f'{seed:04d}.txt' for rid in [a,b]]
        if paths[0].read_bytes() != paths[1].read_bytes():
            different.append(seed)
    out['list0_identity'][b] = {'normal': a, 'same': 2000-len(different),
                               'total': 2000, 'different': different}
    assert not different, (a,b,different[:20])

all_runs = [*normal['runs'], replay['reference'], replay['candidate'],
            clang['reference'], *clang['results']]
for rid in all_runs:
    d=R/rid
    m=json.loads((d/'meta.json').read_text())
    cases=json.loads((d/'result.json').read_text())['cases']
    assert m['status']=='ok'
    assert all(c['score']>0 and all(x>0 for x in (c.get('order_scores') or [])) for c in cases)
    sha=hashlib.sha256((d/'src/main.cpp').read_bytes()).hexdigest()
    if rid.endswith('_dcomp-combo-alt1'): assert sha==frozen
    out['runs'][rid]={'status':m['status'],'count':len(cases),
                      'sha256':sha,'summary':m.get('summary'),
                      'outside_load':m.get('outside_load'),
                      'compiler':m.get('compiler'),'compile_command':m.get('compile_command')}

assert 'pahcer/ への記録 : した' in (N/'t10-final-normal.log').read_text()
out['normal_recorded']=True
(N/'t10-final-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print('List 0 byte identity: 2000/2000 for each solver. All final sources and statuses verified.')
