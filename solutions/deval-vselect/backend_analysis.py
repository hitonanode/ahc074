"""Record same-run timing and physical-state equivalence of implementation changes."""
from pathlib import Path
import json
from analyze import timing,RUNS
from summarize_final import normal
from compare_states import state
HERE=Path(__file__).resolve().parent
PAIRS=[('cache','20261107-051437_deval-vclean','20261107-051437_deval-vcache'),
       ('reciprocal','20261107-052316_deval-vreheat','20261107-052316_deval-vrecip'),
       ('design_O3','20261107-052408_deval-vclean','20261107-052408_deval-vo3'),
       ('all_O3','20261107-054033_deval-vclean','20261107-054033_deval-vallopt'),
       ('compact','20261107-054350_deval-vbranch','20261107-054350_deval-vcompact'),
       ('branch_time','20261107-052723_argon-des-perf-latew105','20261107-052723_deval-vbranch')]
out=[]
for name,a,b in PAIRS:
    x=timing(a);y=timing(b)
    row=dict(name=name,reference=a,candidate=b,normal=normal(a,b),time=dict(reference=x,candidate=y),
             judge_ratio=y['judge']['mean']/x['judge']['mean'])
    if name in ['cache','design_O3','all_O3','compact']:
        left=RUNS/a/'design';right=RUNS/b/'design'
        common=sorted(set(p.name for p in left.glob('*.txt'))&set(p.name for p in right.glob('*.txt')))
        wrong=[p for p in common if state(left/p)!=state(right/p)]
        row.update(physical_states=len(common),physical_mismatches=wrong)
    out.append(row)
    print(name,'judge ratio',row['judge_ratio'],'states',row.get('physical_states'),'mismatches',len(row.get('physical_mismatches',[])),flush=True)
(HERE/'backend_results.json').write_text(json.dumps(out,indent=2)+'\n')
