"""Render audited Task13 summaries without choosing new settings."""
from pathlib import Path
import json
N=Path(__file__).resolve().parent
sets=[('GCC既定・2000件','t13-final-gcc'),('Clang native・500件','t13-final-clang')]
lines=['## 最終比較','', '指定の通常compareを同じ凍結ソースで完了した。負の差が改善、±はseed間の標準誤差。全runは記録済み、WA=0、E=0。ソースhash・件数・記録・表示誤りの監査は`t13-audit.json`。', '']
def f(x,n=6):return f'{x:.{n}f}'
def name(r):return r.split('_',1)[1]
for label,tag in sets:
 d=json.loads((N/(tag+'.json')).read_text());runs=d['runs']
 lines += [f'### {label}', '', 'run: '+', '.join(f'`{r}`'for r in runs), '', '|候補|dual30比 % ± SE|moves/order差 ± SE|勝/分/敗|', '|---|---:|---:|---:|']
 for r in runs[2:]:
  q=d['scores'][r]['all'];p=q['pct'];m=q['moves']
  lines += [f"|{name(r)}|{p['mean']:+.6f} ± {p['se']:.6f}|{m['mean']:+.6f} ± {m['se']:.6f}|{'/'.join(map(str,q['wtl']))}|"]
 lines += ['', 'CLOCK_SCALE適用済みのプログラム時計。各セルは平均 / p99 / 最大、単位は秒。', '', '|版|helper_end|req|end|', '|---|---:|---:|---:|']
 for r in runs:
  t=d['times'][r];cells=[' / '.join(f(t[k][s])for s in ['mean','p99','max'])for k in ['helper_end_sec','req_sec','end_sec']]
  lines += ['|'+name(r)+'|'+'|'.join(cells)+'|']
 lines += ['', 'dual30との対応差（ms、± SE）:', '', '|候補|helper_end|req|end|', '|---|---:|---:|---:|']
 for r in runs[2:]:
  cells=[f"{1000*d['paired'][r][k]['mean']:+.3f} ± {1000*d['paired'][r][k]['se']:.3f}"for k in ['helper_end_sec','req_sec','end_sec']]
  lines += ['|'+name(r)+'|'+'|'.join(cells)+'|']
 lines += ['', '|候補|end>1.80|>1.85|>1.90|>1.93|>2.00|', '|---|---:|---:|---:|---:|---:|']
 for r in runs:
  x=d['times'][r]['end_above'];lines+=['|'+name(r)+'|'+'|'.join(str(x[k])for k in ['1.8','1.85','1.9','1.93','2.0'])+'|']
 if d['count']==2000:
  lines += ['', '|候補|seeds 0–999 % ± SE|seeds 1000–1999 % ± SE|', '|---|---:|---:|']
  for r in runs[2:]:
   cells=[f"{d['scores'][r][k]['pct']['mean']:+.6f} ± {d['scores'][r][k]['pct']['se']:.6f}"for k in ['0-999','1000-1999']]
   lines+=['|'+name(r)+'|'+'|'.join(cells)+'|']
 lines+=['', '締切の診断（全caseで9候補を完了）:', '', '|候補|0反復だった可変段（件数）|helper終了−予算終了 平均 / p99 / 最大 ms|clock読取回数 平均|', '|---|---|---:|---:|']
 for r in runs[2:]:
  q=d['deadline'][r];zero=', '.join(k+':'+str(v['zero_count'])for k,v in q['phase'].items()if v.get('zero_count',0))or'なし';x=q['helper_minus_budget_end']
  lines+=['|'+name(r)+'|'+zero+'|'+' / '.join(f(x[s]*1000,3)for s in ['mean','p99','max'])+'|'+f(q['clock_reads']['mean'],1)+'|']
 lines += ['']
(N/'RESULTS13.md').write_text('\n'.join(lines)+'\n')
print('Wrote RESULTS13.md')
