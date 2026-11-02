#!/usr/bin/env python3
"""高速化前後の同一性検査。時刻以外の既存の全指標を比較する。"""
from pathlib import Path
import argparse,json,math
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');a=p.parse_args()
errors=[];cases=sequences=0;max_abs=0
for f in sorted((ROOT/'results'/a.after).glob('*.jsonl')):
    before=ROOT/'results'/a.before/f.name
    if not before.exists():continue
    b=[json.loads(x) for x in before.read_text().splitlines()]
    c=[json.loads(x) for x in f.read_text().splitlines()]
    assert len(b)==len(c)
    cases+=1;sequences+=len(b)-1
    for i,(br,cr) in enumerate(zip(b,c)):
        for k,bv in br.items():
            if k=='req_sec':continue
            cv=cr[k]
            if isinstance(bv,float):
                max_abs=max(max_abs,abs(bv-cv))
                equal=math.isclose(bv,cv,rel_tol=1e-10,abs_tol=1e-10)
            else:equal=bv==cv
            if not equal:errors.append([f.stem,i,k,bv,cv])
res={'before':a.before,'after':a.after,'cases':cases,'sequences':sequences,'max_float_difference':max_abs,'differences':errors}
(ROOT/'results'/('identity-'+a.before+'-'+a.after+'.json')).write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res))
assert cases>0 and not errors
