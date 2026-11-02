#!/usr/bin/env python3
"""計測記録を一覧化する（CSVを正本として残す）。"""
import json
from pathlib import Path
h=Path(__file__).resolve().parent
rows=[]
for f in sorted(h.glob('*-normal.json')):
    d=json.loads(f.read_text()); c=d['config']['candidate']; v=d['variants'][c]
    x=d['compare']['gobj_after']
    rows.append(f"| {f.stem} | {x['log_pct']:+.4f} ± {x['se_pct']:.4f}% | {x['win']}/{x['tie']}/{x['loss']} | {v['end_sec']['max']:.5f} |")
table='| 計測名（各64件） | gobj_after log比 ± SE | 勝/分/敗 | 候補end_sec最大 |\n|---|---:|---:|---:|\n'+'\n'.join(rows)+'\n'
(h/'EXPERIMENTS.md').write_text('# 実験一覧\n\n'+table)
print(table)
