"""Byte identity and score identity across every saved order list."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('first');p.add_argument('second');p.add_argument('--output',required=True);a=p.parse_args()
r=Path('/home/sato/ahc074/runs');x,y=r/a.first,r/a.second
for d in [x,y]:assert json.loads((d/'meta.json').read_text())['status']=='ok'
cx={c['seed']:c.get('order_scores',[c['score']]) for c in json.loads((x/'result.json').read_text())['cases']}
cy={c['seed']:c.get('order_scores',[c['score']]) for c in json.loads((y/'result.json').read_text())['cases']}
assert cx.keys()==cy.keys()
score_diff=[s for s in cx if cx[s]!=cy[s]]
paths=sorted((x/'out').glob('*.txt'))+sorted((x/'orders').glob('*/out/*.txt'))
different=[str(f.relative_to(x)) for f in paths if f.read_bytes()!=(y/f.relative_to(x)).read_bytes()]
out={'first':a.first,'second':a.second,'n_cases':len(cx),'n_outputs':len(paths),'identical':len(paths)-len(different),'different':different,'score_different_seeds':score_diff}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
raise SystemExit(bool(different or score_diff))
