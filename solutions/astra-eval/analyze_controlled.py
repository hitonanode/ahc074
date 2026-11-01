#!/usr/bin/env python3
"""Summarize a completed paired fixed-design experiment without replaying or editing raw runs.

This reads exported result/metric records plus exact integer design hashes from stderr.
The model-threshold subgroup describes selected forced-mode observations, not a measured
normal-adoption policy. Ranges and the threshold are explicit command-line inputs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read_range(text):
    first, last = map(int, text.split('-'))
    if first < 0 or last <= first:
        raise argparse.ArgumentTypeError('Use a nonempty half-open START-END range')
    return list(range(first, last))


def field(text, name, integer=False):
    number = r'\d+' if integer else r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
    values = re.findall(rf'(?m)^\s*{re.escape(name)}\s*=\s*({number})\s*$', text)
    return (int(values[-1]) if integer else float(values[-1])) if values else None


def fnv_design(path):
    if not path.exists():
        return None
    rows = path.read_bytes().splitlines(keepends=True)[:192]
    if len(rows) != 192 or any(len(row) != 65 or row[-1:] != b'\n' or set(row[:-1])-set(b'01.') for row in rows):
        return None
    value = 14695981039346656037
    for row in rows:
        for byte in row:
            value = ((value ^ byte)*1099511628211) & ((1 << 64)-1)
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def average(values):
    return statistics.mean(values) if values else None


def side_summary(cases):
    valid = [x for x in cases if x['score'] > 0]
    replayed = [x for x in valid if x['replay_metrics_status'] == 'match']
    return {
        'case_count': len(cases), 'valid_score_count': len(valid),
        'average_score': average([x['score'] for x in valid]),
        'average_E': average([x['E'] for x in replayed]),
        'average_T': average([x['T'] for x in replayed]),
        'average_moves_per_request': average([x['T']/x['requests'] for x in replayed]),
        'wa_count': len(cases)-len(valid),
        'over_2sec_count': sum(x['execution_time_sec'] > 2 for x in cases),
        'mean_time_sec': average([x['execution_time_sec'] for x in cases]),
        'max_time_sec': max((x['execution_time_sec'] for x in cases), default=None),
        'replay_metric_missing_or_mismatch_count': len(valid)-len(replayed),
        'stderr_missing_score_line_count': sum(not x['stderr_has_score_line'] for x in cases),
    }


def paired_summary(ids, baseline, candidate, diagnostics):
    present = [i for i in ids if i in baseline and i in candidate]
    valid = [i for i in present if baseline[i]['score'] > 0 and candidate[i]['score'] > 0]
    ratios = [math.log(candidate[i]['score']/baseline[i]['score']) for i in valid]
    avg = average(ratios)
    se = statistics.stdev(ratios)/math.sqrt(len(ratios)) if len(ratios) > 1 else None
    return {
        'case_ids': present, 'missing_case_ids': sorted(set(ids)-set(present)),
        'paired_valid_count': len(valid), 'mean_log_ratio': avg, 'standard_error': se,
        'mean_log_ratio_pct': 100*avg if avg is not None else None,
        'standard_error_pct': 100*se if se is not None else None,
        'wins': sum(candidate[i]['score'] < baseline[i]['score'] for i in valid),
        'ties': sum(candidate[i]['score'] == baseline[i]['score'] for i in valid),
        'losses': sum(candidate[i]['score'] > baseline[i]['score'] for i in valid),
        'baseline': side_summary([baseline[i] for i in present]),
        'candidate': side_summary([candidate[i] for i in present]),
        'initial_design_hash': {
            'matched': sum(diagnostics[i]['initial_design_matches_baseline'] is True for i in present),
            'mismatched': sum(diagnostics[i]['initial_design_matches_baseline'] is False for i in present),
            'missing': sum(diagnostics[i]['initial_design_matches_baseline'] is None for i in present),
        },
        'predicted_delta_missing': sum(diagnostics[i]['relax_predicted_delta'] is None for i in present),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline_run')
    parser.add_argument('candidate_run')
    parser.add_argument('--main-range', type=read_range, default=read_range('0-96'))
    parser.add_argument('--holdout-range', type=read_range, default=read_range('32-96'))
    parser.add_argument('--threshold', type=float, default=-0.15)
    parser.add_argument('--runs-dir', type=Path, default=ROOT/'runs')
    parser.add_argument('--exports-dir', type=Path, default=HERE/'results')
    parser.add_argument('--candidate-source', type=Path)
    parser.add_argument('--output', type=Path, default=HERE/'results/controlled_analysis.json')
    args = parser.parse_args()
    b = json.loads((args.exports_dir/f'{args.baseline_run}.json').read_text())
    c = json.loads((args.exports_dir/f'{args.candidate_run}.json').read_text())
    if c['baseline_run_id'] != args.baseline_run:
        raise ValueError('Candidate export names a different simultaneous baseline')
    baseline = {x['case_id']: x for x in b['cases']}
    candidate = {x['case_id']: x for x in c['cases']}
    diagnostics = {}
    for seed in sorted(set(baseline) & set(candidate)):
        if baseline[seed]['input_sha256'] != candidate[seed]['input_sha256']:
            raise ValueError(f'Different inputs at case {seed}')
        err_path = args.runs_dir/args.candidate_run/'err'/f'{seed:04d}.txt'
        text = err_path.read_text(errors='replace') if err_path.exists() else ''
        # Never read these uint64 values through a float-valued metrics cache.
        initial = field(text, 'initial_design_hash', integer=True)
        final = field(text, 'final_design_hash', integer=True)
        base_hash = fnv_design(args.runs_dir/args.baseline_run/'out'/f'{seed:04d}.txt')
        actual_final = fnv_design(args.runs_dir/args.candidate_run/'out'/f'{seed:04d}.txt')
        diagnostics[seed] = {
            'case_id': seed,
            'baseline_design_fnv1a64': str(base_hash) if base_hash is not None else None,
            'candidate_initial_design_fnv1a64': str(initial) if initial is not None else None,
            'initial_design_matches_baseline': initial == base_hash if initial is not None and base_hash is not None else None,
            'candidate_final_design_fnv1a64': str(final) if final is not None else None,
            'candidate_actual_design_fnv1a64': str(actual_final) if actual_final is not None else None,
            'final_design_matches_stdout': final == actual_final if final is not None and actual_final is not None else None,
            'relax_predicted_delta': field(text, 'relax_predicted_delta'),
            'relax_selected': field(text, 'relax_selected', integer=True),
            'relax_force': field(text, 'relax_force', integer=True),
            'mandatory_requests': field(text, 'mandatory_requests', integer=True),
            'mandatory_failures': field(text, 'mandatory_failures', integer=True),
        }
    comparisons = {
        'fixed_full_sample': paired_summary(args.main_range, baseline, candidate, diagnostics),
        'pre_reserved_holdout': paired_summary(args.holdout_range, baseline, candidate, diagnostics),
    }
    for name, ids in [('exploratory_threshold_full', args.main_range),
                      ('exploratory_threshold_holdout', args.holdout_range)]:
        selected = [i for i in ids if i in diagnostics and diagnostics[i]['relax_predicted_delta'] is not None
                    and diagnostics[i]['relax_predicted_delta'] < args.threshold]
        row = paired_summary(selected, baseline, candidate, diagnostics)
        row['exploratory'] = True
        row['selection'] = f'relax_predicted_delta < {args.threshold}'
        row['selection_metric_missing_in_parent_range'] = sum(i not in diagnostics or diagnostics[i]['relax_predicted_delta'] is None for i in ids)
        row['interpretation'] = 'Conditional subset of the observed forced-mode run; not a measured normal-adoption-policy score.'
        comparisons[name] = row
    current = args.candidate_source or ROOT/'solutions'/args.candidate_run.split('_', 1)[1]/'main.cpp'
    current_hash = digest(current)
    snapshot_hash = digest(args.runs_dir/args.candidate_run/'src/main.cpp')
    result = {
        'schema_version': 1, 'kind': 'controlled_solver_analysis',
        'baseline_run_id': args.baseline_run, 'candidate_run_id': args.candidate_run,
        'baseline_upstream_commit': b['baseline_upstream_commit'], 'input_namespace': b['input_namespace'],
        'ranges_are_half_open': True, 'main_range': [args.main_range[0], args.main_range[-1]+1],
        'pre_reserved_holdout_range': [args.holdout_range[0], args.holdout_range[-1]+1],
        'preexisting_normal_adoption_threshold': args.threshold,
        'current_candidate_source_sha256': current_hash, 'evaluated_candidate_source_sha256': snapshot_hash,
        'current_candidate_matches_evaluated_snapshot': current_hash == snapshot_hash if current_hash else None,
        'baseline_source_sha256': b['source_sha256']['main.cpp'],
        'hash_method': 'FNV-1a64 over the exact first 192 physical 64-character design rows, each including LF; uint64 stderr fields parsed as integers and serialized as decimal strings.',
        'score_source': 'result.json through compact exports; E/T checked against independent replay metrics; no new replay performed.',
        'comparisons': comparisons, 'case_diagnostics': list(diagnostics.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    for name, row in comparisons.items():
        print(name, 'n=', row['paired_valid_count'], 'log%=', row['mean_log_ratio_pct'], '+/-', row['standard_error_pct'],
              'W/T/L=', (row['wins'], row['ties'], row['losses']), 'hash=', row['initial_design_hash'])
    print('Current candidate source matches snapshot:', result['current_candidate_matches_evaluated_snapshot'])


if __name__ == '__main__':
    main()
