#!/usr/bin/env python3
"""既存の測定JSONから、比較表だけを表示する。再実行はしない。"""
from pathlib import Path
import json
p=Path(__file__).resolve().parent
print('| 計測 | 指標 | 件数 | log比平均 ± SE (%) | 勝/分/敗 | 候補end_sec最大 |')
print('|---|---|---:|---:|---:|---:|')
archive=p/'experiments-summary.json'
runs=json.loads(archive.read_text()) if archive.exists() else {}
for f in sorted(p.glob('*.json'),key=lambda q:q.stat().st_mtime):
 d=json.loads(f.read_text())
 if isinstance(d,dict) and 'config' in d and 'compare' in d:runs[f.stem]=d
for name,d in runs.items():
 c=d['config'];metric='sim_moves' if c.get('sim') else 'gobj_after';r=d['compare'].get(metric)
 if not r:continue
 v=d['variants'][c['candidate']];t=v.get('end_sec',{}).get('max')
 print(f"| {name} | {metric} | {r['n']} | {r['log_pct']:+.4f} ± {r['se_pct']:.4f} | {r['win']}/{r['tie']}/{r['loss']} | {t if t is not None else '—'} |")
