#!/usr/bin/env python3
"""Export auditable paired-case results from completed ChatGPT experiment runs."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


def mean(values):
    return statistics.mean(values) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='JSON with groups: [{name, runs, description}]')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('results'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(args.manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {'base_commit': manifest['base_commit'], 'groups': []}
    raw = {'base_commit': manifest['base_commit'], 'runs': {}}
    rows = []
    for group in manifest['groups']:
        arms = []
        for run_id in group['runs']:
            directory = root / 'runs' / run_id
            result = json.loads((directory / 'result.json').read_text())
            meta = json.loads((directory / 'meta.json').read_text())
            metrics = json.loads((directory / 'metrics.json').read_text())['cases']
            source_hash = hashlib.sha256((directory / 'src' / 'main.cpp').read_bytes()).hexdigest()
            for case in result['cases']:
                seed = case['seed']
                if not case.get('artifact_verified'):
                    raise RuntimeError(f'Unverified artifact: {run_id}, seed {seed}')
                for stream, key in [('out', 'output_sha256'), ('err', 'stderr_sha256')]:
                    actual = hashlib.sha256((directory / stream / f'{seed:04d}.txt').read_bytes()).hexdigest()
                    if actual != case[key]:
                        raise RuntimeError(f'Artifact changed after verification: {run_id}, {stream}, seed {seed}')
                m = metrics[str(seed)]
                if m['error'] or m['score'] != case['score'] or m['judge_score'] != case['score']:
                    raise RuntimeError(f'Independent replay mismatch: {run_id}, seed {seed}')
                rows.append({
                    'group': group['name'], 'run_id': run_id, 'seed': seed,
                    'score': case['score'], 'E': m['E'], 'T': m['T'],
                    'moves_per_request': m['T'] / m['requests'],
                    'execution_time_seconds': case['execution_time'],
                    'artifact_verified': True, 'source_sha256': source_hash,
                    'output_sha256': case['output_sha256'], 'stderr_sha256': case['stderr_sha256'],
                })
            raw['runs'][run_id] = {
                'metadata': meta, 'source_sha256': source_hash,
                'result': result, 'metrics': metrics,
            }
            arms.append((run_id, result, metrics))
        base = {case['seed']: case for case in arms[0][1]['cases']}
        comparisons = []
        for run_id, result, metrics in arms:
            cases = result['cases']
            ratios, deltas = [], []
            wins = ties = losses = 0
            diagnostics = {}
            for case in cases:
                original = base[case['seed']]['score']
                score = case['score']
                ratios.append(math.log(score / original))
                deltas.append((score - original) / 1024)
                wins += score < original
                ties += score == original
                losses += score > original
                for key, value in metrics[str(case['seed'])]['stderr'].items():
                    diagnostics.setdefault(key, []).append(value)
            comparisons.append({
                'run_id': run_id, 'cases': len(cases),
                'mean_score': mean([c['score'] for c in cases]),
                'mean_moves_per_request': mean([m['T'] / m['requests'] for m in metrics.values()]),
                'mean_delta_moves_per_request': mean(deltas),
                'mean_log_ratio_percent': 100 * mean(ratios),
                'standard_error_percent': 100 * statistics.stdev(ratios) / math.sqrt(len(ratios)) if len(ratios) > 1 else 0,
                'wins': wins, 'ties': ties, 'losses': losses,
                'total_mistakes': sum(m['E'] for m in metrics.values()),
                'mean_time_seconds': mean([c['execution_time'] for c in cases]),
                'max_time_seconds': max(c['execution_time'] for c in cases),
                'over_two_seconds': sum(c['execution_time'] > 2.0 for c in cases),
                'mean_diagnostics': {key: mean(values) for key, values in diagnostics.items()},
            })
        summary['groups'].append({**group, 'comparisons': comparisons})
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (args.output / 'raw_results.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n')
    with (args.output / 'cases.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for group in summary['groups']:
        print(group['name'])
        for c in group['comparisons']:
            print(f"  {c['run_id']}: {c['mean_moves_per_request']:.6f} moves, "
                  f"{c['mean_log_ratio_percent']:+.3f} +/- {c['standard_error_percent']:.3f}% "
                  f"({c['wins']}/{c['ties']}/{c['losses']}), E={c['total_mistakes']}, "
                  f"max {c['max_time_seconds']:.3f}s")


if __name__ == '__main__':
    main()
