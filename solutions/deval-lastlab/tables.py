"""Render training tables from summarize.py output; no test data are read."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
rows=json.loads((P/'summary.json').read_text())
def fmt(v,scale=1):return f'{scale*v[0]:+.4f} ± {scale*v[1]:.4f}'
lines=['# Task 6 学習試行一覧','',
'全てseed 0–499内。負が改善、±はケース間の標準誤差。多数の試行から選ぶため、この表だけで未使用ケースでの効果を主張しない。通常評価は24並列。replayの時間は、同じreplay内での比較だけに用いる。','',
'## 出力を保つ変更','',
'GCC/Clangはそれぞれ親と比較する。異なるcompiler間の一致を要求したものではない。ソース整理は容量確保のためで、時間短縮が明確でない変更は高速化として数えない。','',
'| 候補 / compiler | 件数 / stdout一致 | map差 ms | anneal差 ms | finish差 ms | req差 ms | judge差 ms | run / 親 |',
'|---|---:|---:|---:|---:|---:|---:|---|']
for z in rows:
    if z['kind']!='speed':continue
    lines.append(f"| {z['run'].split('_',1)[1]} / {z['compiler']} | {z['n']} / {z['identical']} | {fmt(z['map_end_sec'],1000)} | {fmt(z['dv_anneal_sec'],1000)} | {fmt(z['dv_finish_sec'],1000)} | {fmt(z['req_sec'],1000)} | {fmt(z['judge_delta'],1000)} | `{z['run']}` / `{z['ref']}` |")
lines+=['','## 設計または併用の変更','',
'通常500件の同時比較で設計と時間を記録し、各設計を同じ8列で再生した。基準replayは `20261107-164930_deval-flex125-plan3`。時間比は同じnormal compareのargon、p99比較先は同じcompareのnofb。','',
'| 候補 | 列1–7 % | 全8列 % | 実列0 % | 設計差 ms | judge/old | p99 / nofb s | normal / replay |',
'|---|---:|---:|---:|---:|---:|---:|---|']
for z in rows:
    if z['kind']!='quality':continue
    lines.append(f"| {z['tag']} | {fmt(z['fresh'])} | {fmt(z['all'])} | {fmt(z['real'])} | {fmt(z['design_delta'],1000)} | {z['judge_ratio_old']:.5f} | {z['judge_p99'][0]:.5f} / {z['judge_p99'][1]:.5f} | `{z['design']}` / `{z['run']}` |")
lines+=['','## 注文処理のみ','',
'保存設計 `20261107-165305_deval-flex125-plan3`、seed 0–499×4列、基準を先頭にしたcompare。req差は保存設計を読むreplayの中での差であり、最終judge判定はnormal compareで行う。','',
'| 候補 | 全4列 % | 新規1–3 % | 実列0 % | req差 ms | run / 比較元 |',
'|---|---:|---:|---:|---:|---|']
for z in rows:
    if z['kind']!='request':continue
    lines.append(f"| {z['run'].split('_',1)[1]} | {fmt(z['all4'])} | {fmt(z['fresh3'])} | {fmt(z['real'])} | {fmt(z['req_delta'],1000)} | `{z['run']}` / `{z['ref']}` |")
controlled=[z for z in rows if z['kind']=='controlled']
if controlled:
 lines+=['','## rematch削減後の同じ設計での予算調整','',
 '保存設計は `20261107-200401_deval-equalfund6`、seed 0–499×8列。品質の基準はflex125-plan3の164930 replay。req差は同じ保存設計を読むequalfund6に対して測る。候補にはSIMD短縮も含む。', '',
 '| 候補 | 列1–7 % | 全8列 % | 実列0 % | equal-fund親との列1–7差 % | 親とのreq差 ms | run / 親 |',
 '|---|---:|---:|---:|---:|---:|---|']
 for z in controlled:
  lines.append(f"| {z['run'].split('_',1)[1]} | {fmt(z['fresh'])} | {fmt(z['all'])} | {fmt(z['real'])} | {fmt(z['parent_fresh'])} | {fmt(z['req_delta'],1000)} | `{z['run']}` / `{z['ref']}` |")
(P/'TABLES.md').write_text('\n'.join(lines)+'\n')
print('rows',len(rows))
