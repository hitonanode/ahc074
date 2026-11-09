from pathlib import Path
import json
root=Path(__file__).resolve().parent
jobs=[('M100','map-gate100.json'),('M500','map-500.json'),('Mrev','map-rev500.json'),('T','tie-500.json'),('H1','helper-500.json'),('H2','helper-rev500.json'),('R1','retire-500.json'),('R2','retire-rev500.json'),('RF','req-fixed2000.json'),('RN','req-normal2000.json'),('SG','speed-gcc200.json'),('SC','speed-clang200.json')]
refs=[];rows=[];times=[]
for label,file in jobs:
 p=root/file
 if not p.exists():continue
 x=json.loads(p.read_text())
 for j,(r,z) in enumerate(x['comparisons'].items()):
  name=f'{label}{j+1}' if len(x['comparisons'])>1 else label
  refs.append(f'- {name}: `{x["base"]}` / `{r}`')
  score=z['score'];rows.append(f'| {name} | {z["n"]} | {score["mean"]:+.6f} ± {score["se"]:.6f} | '+ '/'.join(map(str,z['wtl']))+f' | {z["wa"]} |')
  t=z['paired_ms'];q=z['arm_p99_ms'];ks=['helper_end_sec','req_sec','end_sec']
  times.append('| '+name+' | '+' | '.join(f'{t[k]["mean"]:+.3f} ± {t[k]["se"]:.3f}' for k in ks)+' | '+' / '.join(f'{q[k][0]:.1f}→{q[k][1]:.1f}' for k in ks)+' |')
text='基準 / 候補のrun-id:\n\n'+'\n'.join(refs)+'\n\n| 比較 | seeds | log比% ± SE | 勝/分/敗 | WA |\n|---|---:|---:|---:|---:|\n'+'\n'.join(rows)+'\n\n時間はms、候補−基準。p99はhelper / request / endの順。\n\n| 比較 | helper ± SE | request ± SE | end ± SE | p99 基準→候補 (H/R/E) |\n|---|---:|---:|---:|---|\n'+'\n'.join(times)+'\n'
(root/'TABLES.md').write_text(text)
