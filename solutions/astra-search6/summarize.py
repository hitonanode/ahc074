#!/usr/bin/env python3
from pathlib import Path
import json
h=Path(__file__).resolve().parent
rows=[]
for p in sorted(h.glob('*.json')):
 d=json.loads(p.read_text())
 if 'compare' not in d or 'gobj_after' not in d['compare']:continue
 c=d['config'];r=d['compare']['gobj_after'];v=d['variants'][c['candidate']]
 rows.append((p.stem,r,v,c))
out='''# 実験一覧

差は100 log(候補/同時計測したas5-g38)の平均±SE、負が改善。固定回数は正しさの診断であり採否に使わない。
各ラベルのCSVがseedごとの生データ、JSONが集計。異なるラベル間の値の差は同時計測ではない。

| ラベル | 件数 | gobj_after比 ± SE (%) | 勝/分/敗 | end_sec最大 | 固定試行数 |
|---|---:|---:|---:|---:|---:|
'''
for name,r,v,c in rows:
 out+=f"| {name} | {r['n']} | {r['log_pct']:+.4f} ± {r['se_pct']:.4f} | {r['win']}/{r['tie']}/{r['loss']} | {v.get('end_sec',{}).get('max',0):.5f} | {c['fixed']} |\n"
(h/'EXPERIMENTS.md').write_text(out)
print(out)
