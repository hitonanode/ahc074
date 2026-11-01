#!/usr/bin/env python3
"""計測JSONを短い表にまとめる。負のlog比が改善、±は標準誤差。"""
import json,pathlib,sys
h=pathlib.Path(__file__).resolve().parent
files=[h/(x+'.json') for x in (sys.argv[1:] or ['final-normal','final-sim','holdout-normal','holdout-sim'])]
for f in files:
 p=json.loads(f.read_text()) if f.exists() else json.loads((h/'experiments-summary.json').read_text())[f.stem]
 if 'compare' not in p: continue
 print(f.stem)
 for b,ds in p['compare'].items():
  for metric in ['gobj_after','sim_moves']:
   if metric not in ds: continue
   d=ds[metric]
   v=p['variants'][b]
   print(f"  {b:24} {metric:12} {d['log_pct']:+.4f} ± {d['se_pct']:.4f}%  {d['win']}/{d['tie']}/{d['loss']}  n={d['n']}  mean={v[metric]['mean']:.6f}")
  for k in ['search_accept','forced_steps','tabu_skips','end_sec']:
   if k in p['variants'][b]:
    d=p['variants'][b][k]
    print(f"    {k}: mean={d['mean']:.5f}, max={d['max']:.5f}")
