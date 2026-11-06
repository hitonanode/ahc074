"""Paired training-seed differences, to distinguish gains from selection noise."""
from pathlib import Path
import json
import numpy as np
from analyze import scores
HERE=Path(__file__).resolve().parent
rows={r['tag']:r for r in map(json.loads,(HERE/'experiments.jsonl').read_text().splitlines())}
reference='reheat2';base=scores(rows[reference]['replay']);out=[]
for tag in ['clean4','beam4obj','reheat4','mix15reheat','reheat6thin','reheat8thin','recip4','kick2','screenpool12','twins2x2','twins3x2']:
    if tag not in rows:continue
    y=scores(rows[tag]['replay']);ids=sorted(s for s in set(y)&set(base) if s<500)
    d=np.array([100*np.log(y[s][1:].mean()/base[s][1:].mean()) for s in ids])
    r=dict(reference=reference,candidate=tag,n=len(d),mean=float(d.mean()),se=float(d.std(ddof=1)/len(d)**.5))
    out.append(r);print(tag,r['mean'],r['se'])
(HERE/'choice_comparisons.json').write_text(json.dumps(out,indent=2)+'\n')
