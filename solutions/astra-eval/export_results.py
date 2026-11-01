#!/usr/bin/env python3
"""Export compact solver comparison records without modifying the original runs.

Scores come only from result.json. E/T come from the independent replay's metrics.json
and are exported only after their score identity is checked against result.json.
Current stderr statistics have explicit per-metric missing counts; cached stderr values
are never used to fill missing tails. No source paths or process environment are exported.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_BASELINE_COMMIT = '800a3030278849158ada3ede2f41401bb72af3d8'
SCORE = re.compile(r'(?m)^\s*Score\s*=\s*(\d+)\s*$')
NUMBER = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_.:/-]*)\s*=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$')
SOURCE_SUFFIXES = {'.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx', '.h', '.ipp', '.inc'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values):
    return statistics.mean(values) if values else None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def numeric_stderr(text):
    result = {}
    for line in text.splitlines():
        match = NUMBER.match(line)
        if match and match[1] != 'Score':
            value = float(match[2])
            if math.isfinite(value):
                result[match[1]] = value
    return result


def export_run(run_dir, input_dir, namespace, expected_inputs):
    result = json.loads((run_dir/'result.json').read_text())
    meta = json.loads((run_dir/'meta.json').read_text())
    if meta.get('status') != 'ok':
        raise ValueError(f'{run_dir.name} is not a completed run')
    metrics_path = run_dir/'metrics.json'
    metric_document = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    metrics = metric_document.get('cases', {})
    sources = {str(path.relative_to(run_dir/'src')): digest(path)
               for path in sorted((run_dir/'src').rglob('*'))
               if path.is_file() and path.suffix in SOURCE_SUFFIXES}
    if 'main.cpp' not in sources:
        raise ValueError(f'{run_dir.name}: no main.cpp source snapshot')
    cases = []
    stderr_rows = []
    stderr_keys = set()
    for original in sorted(result['cases'], key=lambda x: x['seed']):
        seed, score = int(original['seed']), int(original['score'])
        input_path = input_dir/f'{seed:04d}.txt'
        input_hash = digest(input_path)
        if expected_inputs is not None and expected_inputs.get(seed) != input_hash:
            raise ValueError(f'{run_dir.name} case {seed}: input differs from the {namespace} manifest')
        header = input_path.read_text().splitlines()[0].split()
        _, paper_count, _, request_count = map(int, header)
        metric = metrics.get(str(seed))
        metric_state = 'not_applicable_wa' if score == 0 else 'missing'
        e = moves = requests = None
        if score > 0 and metric is not None:
            identity = 2*paper_count*metric.get('E', -1)+metric.get('T', -1)
            matches = (not metric.get('error') and metric.get('score') == score
                       and metric.get('judge_score', score) == score and identity == score
                       and metric.get('requests') == request_count)
            metric_state = 'match' if matches else 'mismatch'
            if matches:
                e, moves, requests = int(metric['E']), int(metric['T']), int(metric['requests'])
        err_path = run_dir/'err'/f'{seed:04d}.txt'
        text = err_path.read_text(errors='replace') if err_path.exists() else ''
        stats = numeric_stderr(text)
        judge_lines = SCORE.findall(text)
        stderr_score = int(judge_lines[-1]) if judge_lines else None
        complete = stderr_score is not None
        stderr_rows.append((stats, complete))
        stderr_keys.update(stats)
        if metric is not None:
            # Names establish missingness; values from a potentially older cache are not imputed.
            stderr_keys.update(metric.get('stderr', {}))
        stdout_path = run_dir/'out'/f'{seed:04d}.txt'
        cases.append({
            'case_id': seed, 'input_sha256': input_hash,
            'stdout_sha256': digest(stdout_path) if stdout_path.exists() else None,
            'score': score, 'execution_time_sec': float(original['execution_time']),
            'wa': score == 0, 'over_2sec': float(original['execution_time']) > 2.0,
            'replay_metrics_status': metric_state, 'E': e, 'T': moves, 'requests': requests,
            'stderr_present': err_path.exists(), 'stderr_has_score_line': complete,
            'stderr_score_matches_result': stderr_score == score if complete else None,
            'stderr_present_metric_count': len(stats),
        })
    stderr_summary = {}
    for key in sorted(stderr_keys):
        values = [row[key] for row, _ in stderr_rows if key in row]
        complete_values = [row[key] for row, complete in stderr_rows if complete and key in row]
        stderr_summary[key] = {
            'mean_present': mean(values), 'present_count': len(values),
            'missing_count': len(cases)-len(values),
            'mean_complete_stderr': mean(complete_values),
            'present_in_complete_stderr_count': len(complete_values),
        }
    valid = [c for c in cases if not c['wa']]
    checked = [c for c in valid if c['replay_metrics_status'] == 'match']
    summary = {
        'case_count': len(cases), 'valid_score_count': len(valid),
        'average_score': mean([c['score'] for c in valid]),
        'average_E': mean([c['E'] for c in checked]),
        'average_T': mean([c['T'] for c in checked]),
        'average_moves_per_request': mean([c['T']/c['requests'] for c in checked]),
        'E_T_case_count': len(checked), 'wa_count': len(cases)-len(valid),
        'over_2sec_count': sum(c['over_2sec'] for c in cases),
        'mean_time_sec': mean([c['execution_time_sec'] for c in cases]),
        'max_time_sec': max((c['execution_time_sec'] for c in cases), default=None),
        'metrics_missing_count': sum(c['replay_metrics_status'] == 'missing' for c in cases),
        'metrics_mismatch_count': sum(c['replay_metrics_status'] == 'mismatch' for c in cases),
        'stderr_missing_file_count': sum(not c['stderr_present'] for c in cases),
        'stderr_missing_score_line_count': sum(not c['stderr_has_score_line'] for c in cases),
        'stderr_score_mismatch_count': sum(c['stderr_score_matches_result'] is False for c in cases),
    }
    compare = meta.get('compare', {})
    group = compare.get('runs', [run_dir.name])
    return {
        'schema_version': 1, 'kind': 'solver_run', 'run_id': run_dir.name,
        'input_namespace': namespace, 'baseline_upstream_commit': UPSTREAM_BASELINE_COMMIT,
        'comparison_group': group, 'baseline_run_id': group[0],
        'source_sha256': sources,
        'raw_record_sha256': {'result': digest(run_dir/'result.json'),
                              'meta': digest(run_dir/'meta.json'),
                              'metrics': digest(metrics_path) if metrics_path.exists() else None},
        'metadata': {
            'status': meta.get('status'), 'compiler': meta.get('compiler'),
            'created_at': meta.get('created_at'), 'started_at': meta.get('started_at'),
            'finished_at': meta.get('finished_at'), 'seed_range': meta.get('seeds'),
            'recorded_in_shared_pahcer': meta.get('record'),
            'compile_options': [x for x in meta.get('compile_command', [])
                                if x in {'-std=c++23', '-O2', '-DCLOCK_SCALE=1.1'}],
        },
        'summary': summary, 'stderr_statistics': stderr_summary, 'cases': cases,
    }


def comparison_row(run, baseline):
    base = {c['case_id']: c for c in baseline['cases']}
    paired = [(c, base[c['case_id']]) for c in run['cases']
              if c['case_id'] in base and c['score'] > 0 and base[c['case_id']]['score'] > 0]
    for case, ref in paired:
        if case['input_sha256'] != ref['input_sha256']:
            raise ValueError('Cannot compare different input contents')
    ratios = [math.log(c['score']/b['score']) for c, b in paired]
    avg = mean(ratios)
    se = statistics.stdev(ratios)/math.sqrt(len(ratios)) if len(ratios) > 1 else None
    return {
        'group_id': baseline['run_id'], 'baseline_run_id': baseline['run_id'], 'run_id': run['run_id'],
        'paired_case_count': len(paired), 'mean_log_ratio': avg, 'standard_error': se,
        'mean_log_ratio_pct': 100*avg if avg is not None else None,
        'standard_error_pct': 100*se if se is not None else None,
        'wins': sum(c['score'] < b['score'] for c, b in paired),
        'ties': sum(c['score'] == b['score'] for c, b in paired),
        'losses': sum(c['score'] > b['score'] for c, b in paired),
        **run['summary'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_ids', nargs='+', help='Completed run IDs; group members are added automatically')
    parser.add_argument('--runs-dir', type=Path, default=ROOT/'runs')
    parser.add_argument('--input-dir', type=Path, default=ROOT/'tools/in')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).with_name('results'))
    parser.add_argument('--input-namespace', default='astra-generated-v1')
    args = parser.parse_args()
    expected = None
    if args.input_namespace == 'astra-generated-v1':
        with Path(__file__).with_name('generated_manifest.csv').open() as fp:
            expected = {int(row['case_id']): row['sha256'] for row in csv.DictReader(fp)}
    pending = list(args.run_ids)
    selected = set()
    while pending:
        run_id = pending.pop()
        if run_id in selected:
            continue
        if Path(run_id).name != run_id:
            parser.error('Use a run ID, not a path')
        meta = json.loads((args.runs_dir/run_id/'meta.json').read_text())
        selected.add(run_id)
        pending += [x for x in meta.get('compare', {}).get('runs', []) if x not in selected]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for run_id in sorted(selected):
        exported = export_run(args.runs_dir/run_id, args.input_dir, args.input_namespace, expected)
        write_json(args.output_dir/f'{run_id}.json', exported)
        print(run_id, 'cases', exported['summary']['case_count'],
              'replay mismatches', exported['summary']['metrics_mismatch_count'],
              'stderr missing score lines', exported['summary']['stderr_missing_score_line_count'])
    # Keep earlier exported groups when a later invocation adds new runs.
    all_runs = {}
    for path in sorted(args.output_dir.glob('*.json')):
        value = json.loads(path.read_text())
        if value.get('kind') == 'solver_run':
            all_runs[value['run_id']] = value
    rows = []
    for run_id, run in sorted(all_runs.items()):
        baseline_id = run['baseline_run_id']
        if baseline_id not in all_runs:
            raise ValueError(f'Missing exported baseline {baseline_id}')
        rows.append(comparison_row(run, all_runs[baseline_id]))
    with (args.output_dir/'comparisons.csv').open('w', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(args.output_dir/'summary.json', {
        'schema_version': 1, 'kind': 'solver_comparisons',
        'baseline_upstream_commit': UPSTREAM_BASELINE_COMMIT,
        'score_source': 'result.json; score 0 treated as WA and excluded from ratio/score means',
        'E_T_source': 'independent Python replay metrics; score identity checked before export',
        'ratio_definition': 'mean ln(candidate score / paired baseline score); negative is better',
        'standard_error_definition': 'sample standard deviation of paired log ratios / sqrt(n)',
        'stderr_policy': 'current files only; no cached-value imputation; missing counts per metric',
        'run_count': len(rows), 'comparisons': rows,
    })
    print('Wrote comparisons.csv and summary.json; raw runs were read only')


if __name__ == '__main__':
    main()
