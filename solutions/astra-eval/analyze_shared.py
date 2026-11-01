#!/usr/bin/env python3
"""Read-only analysis of completed baseline/union/shared comparisons; no solution replay."""
import argparse
import json
from pathlib import Path
import statistics

from analyze_controlled import digest, field, fnv_design
from export_results import comparison_row

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COUNTS = [
    'relax_selected', 'relax_force', 'shared_attempted', 'shared_explored', 'shared_selected',
    'shared_rollbacks', 'shared_helpers', 'shared_reuse_events', 'shared_punched_handles',
    'shared_punched_generic', 'mandatory_targets', 'mandatory_requests', 'mandatory_failures',
    'fast_requests', 'plan_failures', 'unsafe_plans', 'self_wrong',
]
VALUES = [
    'relax_predicted_delta', 'relax_actual_model_delta', 'shared_explored_model_delta',
    'shared_best_model_delta', 'shared_selected_model_delta', 'relax_union_saved',
    'shared_end_sec', 'req_sec', 'end_sec',
]


def stats(values, total):
    present = [x for x in values if x is not None]
    return {'present_count': len(present), 'missing_count': total-len(present),
            'sum': sum(present) if present else None,
            'mean': statistics.mean(present) if present else None,
            'min': min(present) if present else None, 'max': max(present) if present else None}


def inspect_candidate(candidate, runs_dir, baseline_hashes):
    run_id = candidate['run_id']
    rows = []
    for case in candidate['cases']:
        seed = case['case_id']
        err_path = runs_dir/run_id/'err'/f'{seed:04d}.txt'
        text = err_path.read_text(errors='replace') if err_path.exists() else ''
        initial, final = (field(text, name, integer=True) for name in ['initial_design_hash', 'final_design_hash'])
        initial_ref = baseline_hashes.get(seed)
        output_hash = fnv_design(runs_dir/run_id/'out'/f'{seed:04d}.txt')
        row = {
            'case_id': seed,
            'initial_design_hash_decimal': str(initial) if initial is not None else None,
            'baseline_design_hash_decimal': str(initial_ref) if initial_ref is not None else None,
            'final_design_hash_decimal': str(final) if final is not None else None,
            'stdout_design_hash_decimal': str(output_hash) if output_hash is not None else None,
            'initial_matches_baseline': initial == initial_ref if initial is not None and initial_ref is not None else None,
            'final_matches_stdout': final == output_hash if final is not None and output_hash is not None else None,
        }
        row.update({name: field(text, name, integer=True) for name in COUNTS})
        row.update({name: field(text, name) for name in VALUES})
        rows.append(row)
    snapshot = digest(runs_dir/run_id/'src/main.cpp')
    current = digest(ROOT/'solutions'/run_id.split('_', 1)[1]/'main.cpp')
    hashes = {}
    for name in ['initial_matches_baseline', 'final_matches_stdout']:
        hashes[name] = {'matched': sum(row[name] is True for row in rows),
                        'mismatched': sum(row[name] is False for row in rows),
                        'missing': sum(row[name] is None for row in rows)}
    return {
        'run_id': run_id, 'source_snapshot_sha256': snapshot, 'current_source_sha256': current,
        'current_source_matches_snapshot': current == snapshot if current else None,
        'summary': candidate['summary'], 'hash_checks': hashes,
        'numeric_metrics': {name: stats([row[name] for row in rows], len(rows)) for name in COUNTS+VALUES},
        'cases_with_shared_selection': sum((row['shared_selected'] or 0) > 0 for row in rows),
        'cases_with_helper_reuse': sum((row['shared_reuse_events'] or 0) > 0 for row in rows),
        'cases': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline_run')
    parser.add_argument('union_run')
    parser.add_argument('shared_run')
    parser.add_argument('--phase', choices=['pilot', 'holdout'], required=True)
    parser.add_argument('--runs-dir', type=Path, default=ROOT/'runs')
    parser.add_argument('--exports-dir', type=Path, default=HERE/'results')
    parser.add_argument('--output', type=Path, default=HERE/'results/shared_analysis.json')
    args = parser.parse_args()
    runs = [json.loads((args.exports_dir/f'{run_id}.json').read_text())
            for run_id in [args.baseline_run, args.union_run, args.shared_run]]
    baseline, union, shared = runs
    if any(run['baseline_run_id'] != args.baseline_run for run in runs):
        raise ValueError('Runs do not share the supplied simultaneous baseline')
    case_ids = [{case['case_id'] for case in run['cases']} for run in runs]
    if any(ids != case_ids[0] for ids in case_ids):
        raise ValueError('Completed comparisons must have the same case IDs')
    baseline_hashes = {case['case_id']: fnv_design(args.runs_dir/args.baseline_run/'out'/f"{case['case_id']:04d}.txt")
                       for case in baseline['cases']}
    comparisons = {
        'union_vs_baseline': comparison_row(union, baseline),
        'shared_vs_baseline': comparison_row(shared, baseline),
        'shared_vs_union': comparison_row(shared, union),
    }
    candidates = {'union': inspect_candidate(union, args.runs_dir, baseline_hashes),
                  'shared': inspect_candidate(shared, args.runs_dir, baseline_hashes)}
    experiment = {
        'phase': args.phase, 'baseline_run_id': args.baseline_run, 'input_namespace': baseline['input_namespace'],
        'case_ids': sorted(baseline_hashes), 'baseline': {'run_id': args.baseline_run, 'summary': baseline['summary'],
        'source_snapshot_sha256': baseline['source_sha256']['main.cpp'],
        'snapshot_matches_current_imp_gla': baseline['source_sha256']['main.cpp'] == digest(ROOT/'solutions/imp-gla/main.cpp')},
        'comparisons': comparisons, 'candidates': candidates,
    }
    document = json.loads(args.output.read_text()) if args.output.exists() else {
        'schema_version': 1, 'kind': 'shared_helper_analysis',
        'score_source': 'Completed result.json exports; E/T checked against cached independent replay metrics. No new replay.',
        'comparison_interpretation': '100 * mean(log(candidate score / reference score)); lower is better. Uncertainty is paired sample standard error, not a confidence interval.',
        'hash_method': 'Exact uint64 initial_design_hash from stderr versus FNV-1a64 over baseline first 192 design lines including LF.',
        'model_delta_warning': 'Reported design-model deltas and reuse counts are diagnostics, not measured score changes.',
        'experiments': [],
    }
    document['comparison_interpretation'] = '100 * mean(log(candidate score / reference score)); lower is better. Uncertainty is paired sample standard error, not a confidence interval.'
    document['experiments'] = [x for x in document['experiments'] if x['baseline_run_id'] != args.baseline_run]+[experiment]
    pilots = [x for x in document['experiments'] if x['phase'] == 'pilot']
    if pilots:
        pilot = pilots[0]
        for item in document['experiments']:
            if item['phase'] == 'holdout':
                item['frozen_source_comparison_with_pilot'] = {
                    name: item['candidates'][name]['source_snapshot_sha256'] == pilot['candidates'][name]['source_snapshot_sha256']
                    for name in ['union', 'shared']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    for name, row in comparisons.items():
        print(args.phase, name, 'n=', row['paired_case_count'], 'log%=', row['mean_log_ratio_pct'], '+/-', row['standard_error_pct'],
              'W/T/L=', (row['wins'], row['ties'], row['losses']))
    for name, candidate in candidates.items():
        print(name, 'hash checks', candidate['hash_checks'], 'source matches', candidate['current_source_matches_snapshot'])
    print('Shared diagnostics:', {name: candidates['shared']['numeric_metrics'][name]
                                 for name in ['shared_selected', 'shared_reuse_events', 'shared_helpers',
                                              'shared_punched_handles', 'shared_punched_generic', 'shared_selected_model_delta']})


if __name__ == '__main__':
    main()
