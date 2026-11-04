#!/usr/bin/env python3
"""Read saved designs and stderr; never run the solver. Cache only in head-steer.

Run with python -B, under the evaluation lock when computing uncached proxies.
Uses the unchanged dsel-probe/proxy.py definition, including its final-design convention.
"""
import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "dsel-probe"))
from proxy import proxies
from colfix import barcode_hash_of_input, load_design

RUNS = Path('/home/sato/ahc074/runs')
LINE = re.compile(r'^([a-zA-Z_][\w]*) = ([+-]?[0-9.]+(?:e[+-]?[0-9]+)?)$', re.M)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('runs', nargs='+')
    p.add_argument('--seeds', default='0-200')
    p.add_argument('--proxy', action='store_true')
    args = p.parse_args()
    lo, hi = map(int, args.seeds.split('-'))
    all_rows = []
    for run in args.runs:
        cache = HERE / (run + '.proxy.json')
        saved = json.loads(cache.read_text()) if cache.exists() else {}
        rows = []
        for seed in range(lo, hi):
            raw = (RUNS / run / 'err' / f'{seed:04d}.txt').read_text()
            row = {k: float(v) for k, v in LINE.findall(raw)}
            row['anneal_sec'] = row['anneal_end_sec'] - row['map_end_sec']
            row['climb_sec'] = row['climb_end_sec'] - row['anneal_end_sec']
            row['design_after_map_sec'] = row['perforation_end_sec'] - row['map_end_sec']
            if args.proxy:
                if str(seed) not in saved:
                    design = load_design(RUNS / run / 'design' / (barcode_hash_of_input(seed) + '.txt'))
                    saved[str(seed)] = proxies(design)
                row.update(saved[str(seed)])
            rows.append(row)
        if args.proxy:
            cache.write_text(json.dumps(saved, indent=2) + '\n')
        all_rows.append(rows)
        print(run, f'seeds {lo}-{hi}', flush=True)
        keys = ['anneal_sec', 'climb_sec', 'design_after_map_sec', 'model_cost', 'model_col', 'model_hole',
                'model_gc', 'proxy_before', 'proxy_after', 'proxy_final', 'head_table_sec', 'head_trials',
                'head_accepts', 'head_model_change', 'climb_accepted', 'climb_evaluated', 'climb_cached', 'end_sec']
        for key in keys:
            if key not in rows[0]:
                continue
            values = [r[key] for r in rows]
            line = f'  {key}: {statistics.mean(values):.8f}'
            if len(all_rows) > 1 and key in all_rows[0][0]:
                delta = [r[key] - b[key] for r, b in zip(rows, all_rows[0])]
                se = statistics.stdev(delta) / math.sqrt(len(delta)) if len(delta) > 1 else 0
                line += f'  difference {statistics.mean(delta):+.8f} +/- {se:.8f}'
            print(line, flush=True)
        meta = json.loads((RUNS / run / 'meta.json').read_text())
        print('  outside_load:', meta.get('outside_load'), flush=True)


if __name__ == '__main__':
    main()
