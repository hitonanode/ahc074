"""Summarize completed Task12 screens only; run under flock + nice."""
from pathlib import Path
import json
N=Path(__file__).resolve().parent;R=Path('/home/sato/ahc074/runs')
lines=['# Task 12: 測定表','','差は各runの基準に対する対応差、±はseed単位のSE。replay時間は同時比較の差だけを読む。GCCは既定、clangはnative。外部負荷警告のある時間は採否に使わない。','','|試験 / 基準run|N×列|候補run|差 % ± SE|req差 ms ± SE|helper差 ms ± SE|stdout一致|外部負荷 mean/max core|','|---|---:|---|---:|---:|---:|---:|---:|']
for f in sorted(N.glob('t12-*.json')):
 if f.name.startswith('t12-final-'):continue
 j=json.loads(f.read_text())
 if not isinstance(j,dict) or 'results' not in j or 'reference' not in j:continue
 n=j['seeds'][1]-j['seeds'][0];orders=j['orders']
 for rid,v in j['results'].items():
  p=v['score_pct'];m=v['metrics']
  def cell(k):
   q=m.get(k,{}).get('paired');return '—' if not q else f"{1000*q['mean']:+.3f} ± {1000*q['se']:.3f}"
  load=json.loads((R/rid/'meta.json').read_text()).get('outside_load',{})
  ident=v['identity']
  # Keep the complete load object in JSON originals; format known fields only.
  mean=load.get('mean_cores',load.get('mean'));mx=load.get('max_cores',load.get('max'))
  ls=f'{mean}/{mx}' if mean is not None else str(load)
  if mean is not None and (mean>0.5 or mx>3):ls+='（時間を除外）'
  lines.append(f"|{f.stem}<br>`{j['reference']}`|{n}×{orders}|`{rid}`|{p['mean']:+.6f} ± {p['se']:.6f}|{cell('req_sec')}|{cell('helper_end_sec')}|{ident['same']}/{ident['total']}|{ls}|")
(N/'TABLES12.md').write_text('\n'.join(lines)+'\n')
