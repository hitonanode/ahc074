#!/usr/bin/env python3
"""Reproduce the compact representation-coverage report from the frozen baseline outputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess

from verify_punch_witnesses import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODES = [
    ('none', 'helper-allcols', 'helper_probe', ['all-columns']),
    ('h_single', 'helper-punch-single', 'helper_probe', ['all-columns', 'punch-single']),
    ('h_all', 'helper-punch', 'helper_probe', ['all-columns', 'punch']),
    ('hg_single', 'helper-punch-g-single', 'helper_punch_g_probe', ['single-helpers']),
    ('hg_all', 'helper-punch-g', 'helper_punch_g_probe', []),
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse', action='store_true', help='Use existing results/*.csv and *.txt')
    parser.add_argument('--input-dir', type=Path, default=ROOT/'tools/in')
    args = parser.parse_args()
    results = HERE/'results'
    results.mkdir(exist_ok=True)
    manifest = json.loads((HERE/'reference_manifest.json').read_text())
    by_case = {x['case_id']: x for x in manifest['entries']}
    summary = []
    verified = []
    for seed in range(8):
        input_path = args.input_dir/f'{seed:04d}.txt'
        reference = HERE/'reference-output'/f'{seed:04d}.txt'
        assert hashlib.sha256(input_path.read_bytes()).hexdigest() == by_case[seed]['input_sha256'], 'Wrong input namespace'
        assert hashlib.sha256(reference.read_bytes()).hexdigest() == by_case[seed]['reference_output_sha256'], 'Wrong baseline output'
        for mode, stem, binary, flags in MODES:
            csv_path = results/f'{stem}-{seed:04d}.csv'
            txt_path = results/f'{stem}-{seed:04d}.txt'
            if not args.reuse:
                run = subprocess.run([str(HERE/binary), str(input_path), str(reference), *flags],
                                     text=True, capture_output=True, check=True)
                csv_path.write_text(run.stdout)
                txt_path.write_text(run.stderr)
            rows = list(csv.DictReader(csv_path.open()))
            denominator = int(re.search(r'incompatible_single_pairs = (\d+)', txt_path.read_text())[1])
            best = {}
            shallow = set()
            for row in rows:
                key = (int(row['u']), int(row['v']))
                if mode.startswith('hg'):
                    holes = sum(int(row[f'{kind}_punch_{side}']) for kind in ['g', 'h'] for side in ['u', 'v'])
                    is_shallow = int(row['shallow_both']) != 0
                else:
                    holes = int(row.get('punch_u', 0)) + int(row.get('punch_v', 0))
                    is_shallow = int(row.get('shallow_u', 0)) > 0 and int(row.get('shallow_v', 0)) > 0
                best[key] = min(best.get(key, holes), holes)
                if is_shallow:
                    shallow.add(key)
            summary.append({
                'case_id': seed, 'mode': mode, 'incompatible_pairs': denominator,
                'rescued_pairs': len(best), 'rescued_column_assignments': len(rows),
                'shallow_both_pairs': len(shallow),
                'median_selected_total_punches': statistics.median(best.values()),
                'max_selected_total_punches': max(best.values()),
                'minimum_handle_difference': min(int(row['hdiff']) for row in rows),
            })
            if mode.startswith('hg'):
                checked = verify(input_path, reference, csv_path, 200)
                verified.append({'case_id': seed, 'mode': mode, 'sample_seed': 74,
                                 'sampled_column_assignments': checked//2,
                                 'verified_direction_witnesses': checked,
                                 'generic_permutations_considered': 720,
                                 'checks': ['target_generic_display', 'target_handle_agreement',
                                            'helper_own_handle_retained', 'all_original_helper_owners_core_representable'],
                                 'passed': True})
    with (HERE/'coverage.csv').open('w', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (HERE/'witness_verification.json').write_text(json.dumps({
        'input_namespace': manifest['input_namespace'],
        'baseline_run_id': manifest['baseline_run_id'],
        'algorithm': 'independent Python enumeration of 720 generic permutations; no DAG closure code reused',
        'total_verified_directions': sum(x['verified_direction_witnesses'] for x in verified),
        'results': verified,
    }, indent=2)+'\n')
    for mode, *_ in MODES:
        subset = [x for x in summary if x['mode'] == mode]
        print(mode, 'rescued', sum(x['rescued_pairs'] for x in subset), '/', sum(x['incompatible_pairs'] for x in subset),
              'shallow both', sum(x['shallow_both_pairs'] for x in subset))
    print('Wrote coverage.csv and witness_verification.json')

if __name__ == '__main__':
    main()
