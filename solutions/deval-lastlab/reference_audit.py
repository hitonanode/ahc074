"""Check the replay control's labels and error counters too (run under flock)."""
from pathlib import Path
import re,json,sys
P=Path(__file__).resolve().parent;D=P.parent/sys.argv[1];R=Path('/home/sato/ahc074/runs')
x=json.loads((D/'final-metrics.json').read_text());rid=x['run_ids']['reference'];d=R/rid
assert json.loads((d/'meta.json').read_text())['status']=='ok'
cases={int(c['seed']):c for c in json.loads((d/'result.json').read_text())['cases']}
ro=len(next(iter(cases.values()))['order_scores']);keys=['self_wrong','op_label_errors','plan_failures','unsafe_plans'];totals=dict.fromkeys(keys,0);matched=0
for order in range(ro):
 ep=d/('err' if order==0 else f'orders/{order}/err');fs=list(ep.glob('*.txt'));assert len(fs)==len(cases)
 for f in fs:
  s=f.read_text()
  for key in keys:
   v=re.findall(r'^'+key+r' = (\S+)$',s,re.M);assert v;totals[key]+=int(float(v[-1]))
  seen=set();moves=0
  for match in re.finditer(r'^@ops (\d+) = ?(.*)$',s,re.M):
   q=int(match.group(1));assert q not in seen;seen.add(q)
   for token in match.group(2).split():
    _,sep,n=token.partition('*');moves+=int(n) if sep else 1
  assert seen==set(range(1024)) and moves==cases[int(f.stem)]['order_scores'][order],f
  matched+=1
assert not any(totals.values())
out={'reference':rid,'n':len(cases),'orders':ro,'trace_moves_match_score':matched,'errors':totals}
(D/'reference-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
