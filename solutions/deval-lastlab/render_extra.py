from pathlib import Path
import json
P=Path(__file__).resolve().parent
rows=json.loads((P/'normal-frontier.json').read_text())
lines=['## 最終候補を絞る通常500件の測定','',
'全て学習seed 0–499、24並列。正のp99差はこの比較では時間条件を満たさなかったことを表す。最終採否には事前固定した規則と2000件同時比較を用いる。','',
'| 候補 | flex比 % ± SE | judge/old | p99−nofb ms | 設計差 ms | req差 ms | run |','|---|---:|---:|---:|---:|---:|---|']
for z in rows:
 def fmt(v,scale=1):return f'{v[0]*scale:+.4f} ± {v[1]*scale:.4f}'
 lines.append(f"| {z['run'].split('_',1)[1]} | {fmt(z['normal_delta'])} | {z['ratio_old']:.5f} | {(z['p99']-z['p99_nofb'])*1000:+.3f} | {fmt(z['helper_end_sec'],1000)} | {fmt(z['req_sec'],1000)} | `{z['run']}` |")
lines+=['','## 出力一致の追加確認','','`-march=native`の時間は採否に使わず、出力一致の検証だけに用いた。','',
'| 比較 | compiler | 件数 | stdout一致 |','|---|---|---:|---:|']
for z in json.loads((P/'identity-extra.json').read_text()):
 cc=('Clang' if 'clang' in z['compiler'].lower() else 'GCC')+(' native' if '-march=native' in z['flags'] else '')
 lines.append(f"| `{z['reference']}` → `{z['candidate']}` | {cc} | {z['n']} | {z['stdout_identical']} |")
(P/'EXTRA-TABLES.md').write_text('\n'.join(lines)+'\n')
