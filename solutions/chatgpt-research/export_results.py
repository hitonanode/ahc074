#!/usr/bin/env python3
"""Export paired measurements, per-case scores, and provenance from saved runs.

No solver is run. Existing runs and repository evaluation history are not edited.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def load(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exclude', action='append', default=[], help='run-id prefix to exclude')
    parser.add_argument('--run-prefix', action='append', default=[], help='only export these run prefixes')
    args = parser.parse_args()
    destination = HERE / 'results'
    destination.mkdir(exist_ok=True)
    summaries, cases, provenance, exclusions = [], [], {}, []
    for metafile in sorted((ROOT / 'runs').glob('*/meta.json')):
        run = metafile.parent
        meta = load(metafile)
        comparison = meta.get('compare', {})
        if comparison.get('index', 0) < 1 or meta.get('status') != 'ok':
            continue
        if args.run_prefix and not any(run.name.startswith(p) for p in args.run_prefix):
            continue
        baseline = ROOT / 'runs' / comparison['runs'][0]
        bmeta = load(baseline / 'meta.json')
        invalid_replay = meta['summary'].get('replay_mismatch', 0) or bmeta['summary'].get('replay_mismatch', 0)
        if any(run.name.startswith(p) for p in args.exclude) or invalid_replay:
            exclusions.append({'run': run.name, 'baseline': baseline.name,
                               'reason': 'explicitly excluded' if not invalid_replay else 'replay mismatch'})
            continue
        arms = []
        for directory, metadata in ((baseline, bmeta), (run, meta)):
            result = load(directory / 'result.json')
            metrics = load(directory / 'metrics.json')['cases']
            rows = {r['seed']: r for r in result['cases']}
            source = directory / 'src' / 'main.cpp'
            provenance[directory.name] = {
                'source_sha256': digest(source),
                'compile_command': metadata['compile_command'],
                'compiler': metadata['compiler'],
                'parameters': metadata.get('evaluation_adapter', {}),
                'comment': metadata['comment'],
                'source_snapshot_git': metadata.get('source', {}).get('git'),
                'seeds': metadata['seeds'],
                'summary': metadata['summary'],
                'result_sha256': digest(directory / 'result.json'),
            }
            arms.append((rows, metrics))
        br, bm = arms[0]
        nr, nm = arms[1]
        seeds = sorted(set(br) & set(nr))
        valid = [s for s in seeds if br[s]['score'] > 0 and nr[s]['score'] > 0]
        logs = [math.log(nr[s]['score'] / br[s]['score']) for s in valid]
        avg = statistics.mean(logs) if logs else None
        se = statistics.stdev(logs) / math.sqrt(len(logs)) if len(logs) > 1 else None
        def mean_metric(metrics, key):
            vs = [metrics[str(s)].get(key) for s in valid]
            return statistics.mean(v for v in vs if v is not None)
        def mean_stderr(metrics, key):
            vs = [metrics[str(s)].get('stderr', {}).get(key) for s in valid]
            vs = [v for v in vs if v is not None]
            return statistics.mean(vs) if vs else None
        row = {
            'baseline_run': baseline.name, 'candidate_run': run.name,
            'cases': len(seeds), 'valid_pairs': len(valid),
            'baseline_mean_score': statistics.mean(br[s]['score'] for s in valid),
            'candidate_mean_score': statistics.mean(nr[s]['score'] for s in valid),
            'baseline_mean_moves_per_request': mean_metric(bm, 'ops_mean'),
            'candidate_mean_moves_per_request': mean_metric(nm, 'ops_mean'),
            'mean_log_ratio_percent': 100 * avg if avg is not None else None,
            'standard_error_percent': 100 * se if se is not None else None,
            'wins': sum(nr[s]['score'] < br[s]['score'] for s in valid),
            'ties': sum(nr[s]['score'] == br[s]['score'] for s in valid),
            'losses': sum(nr[s]['score'] > br[s]['score'] for s in valid),
            'baseline_WA': sum(br[s]['score'] == 0 for s in seeds),
            'candidate_WA': sum(nr[s]['score'] == 0 for s in seeds),
            'baseline_mean_E': mean_metric(bm, 'E'), 'candidate_mean_E': mean_metric(nm, 'E'),
            'baseline_over_2s': sum(br[s]['execution_time'] > 2 for s in seeds),
            'candidate_over_2s': sum(nr[s]['execution_time'] > 2 for s in seeds),
            'baseline_max_seconds': max(br[s]['execution_time'] for s in seeds),
            'candidate_max_seconds': max(nr[s]['execution_time'] for s in seeds),
        }
        for key in ('fast_requests', 'generic_moves', 'gate_multiway', 'gate_arity', 'gate_full',
                    'alias_added', 'alias_selected', 'alias_candidates_evaluated', 'self_wrong'):
            row['baseline_' + key] = mean_stderr(bm, key)
            row['candidate_' + key] = mean_stderr(nm, key)
        holdout = [s for s in valid if 100008 <= s < 100064]
        if holdout:
            hl = [math.log(nr[s]['score'] / br[s]['score']) for s in holdout]
            row['holdout_100008_100063'] = {
                'cases': len(holdout),
                'baseline_mean_score': statistics.mean(br[s]['score'] for s in holdout),
                'candidate_mean_score': statistics.mean(nr[s]['score'] for s in holdout),
                'baseline_mean_moves_per_request': statistics.mean(bm[str(s)]['ops_mean'] for s in holdout),
                'candidate_mean_moves_per_request': statistics.mean(nm[str(s)]['ops_mean'] for s in holdout),
                'mean_log_ratio_percent': 100 * statistics.mean(hl),
                'standard_error_percent': 100 * statistics.stdev(hl) / math.sqrt(len(hl)) if len(hl) > 1 else None,
                'wins': sum(nr[s]['score'] < br[s]['score'] for s in holdout),
                'ties': sum(nr[s]['score'] == br[s]['score'] for s in holdout),
                'losses': sum(nr[s]['score'] > br[s]['score'] for s in holdout),
            }
        summaries.append(row)
        for seed in seeds:
            bc, nc = br[seed], nr[seed]
            bmetrics, nmetrics = bm.get(str(seed), {}), nm.get(str(seed), {})
            cases.append({
                'baseline_run': baseline.name, 'candidate_run': run.name, 'seed': seed,
                'baseline_score': bc['score'], 'candidate_score': nc['score'],
                'baseline_E': bmetrics.get('E'), 'candidate_E': nmetrics.get('E'),
                'baseline_T': bmetrics.get('T'), 'candidate_T': nmetrics.get('T'),
                'baseline_seconds': bc['execution_time'], 'candidate_seconds': nc['execution_time'],
                'baseline_fast_requests': bmetrics.get('stderr', {}).get('fast_requests'),
                'candidate_fast_requests': nmetrics.get('stderr', {}).get('fast_requests'),
                'input_sha256': digest(ROOT / 'tools' / 'in' / f'{seed:04d}.txt'),
                'baseline_output_sha256': digest(baseline / 'out' / f'{seed:04d}.txt'),
                'candidate_output_sha256': digest(run / 'out' / f'{seed:04d}.txt'),
            })
    for name, data in [('summary.json', summaries), ('provenance.json', provenance),
                       ('excluded_runs.json', exclusions)]:
        (destination / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    if cases:
        with (destination / 'cases.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(cases[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(cases)
    for x in summaries:
        print(f"{x['candidate_run']} n={x['valid_pairs']} "
              f"{x['baseline_mean_moves_per_request']:.5f} -> "
              f"{x['candidate_mean_moves_per_request']:.5f} "
              f"log%={x['mean_log_ratio_percent']:+.4f} +/- "
              f"{x['standard_error_percent']:.4f} "
              f"W/D/L={x['wins']}/{x['ties']}/{x['losses']}")

if __name__ == '__main__':
    main()
