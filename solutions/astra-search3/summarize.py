#!/usr/bin/env python3
"""計測JSONの主要値を表示する。第2引数以降で対象を絞れる。"""
import json, pathlib, sys
here=pathlib.Path(__file__).resolve().parent
for arg in sys.argv[1:]:
    path=here/(arg+'.json')
    s=json.loads(path.read_text()) if path.exists() else json.loads((here/'experiments-summary.json').read_text())[arg]
    print(arg)
    for b,v in s['variants'].items():
        print(' ',b, ' '.join(f'{k}={v[k]["mean"]:.6g} (max {v[k]["max"]:.6g})' for k in ['gobj_after','sim_moves','end_sec','search_exact_evals','search_accept','forced_steps','direct_steps','history_skips'] if k in v))
    for b,v in s['compare'].items():
        for k in ['gobj_after','sim_moves']:
            if k in v:
                r=v[k];print(f'  {b} {k}: {r["log_pct"]:+.4f} ± {r["se_pct"]:.4f}% {r["win"]}/{r["tie"]}/{r["loss"]} n={r["n"]}')
