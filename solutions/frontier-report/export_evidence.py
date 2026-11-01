#!/usr/bin/env python3
"""Export verified per-case evidence without committing generated inputs or full traces."""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import replay

GROUPS = {
    'timed16': ('20261101-050606_', ['imp-lean', 'frontier-clique', 'frontier-clique10', 'frontier-replica']),
    'controlled64': ('20261101-052923_', ['imp-lean', 'frontier-lattice', 'frontier-replica', 'frontier-replica-one']),
}
STATS = ['generic_moves', 'fast_requests', 'lattice_accepted', 'lattice_nonlinear_windows',
         'lattice_valid_trials', 'lattice_refine_before', 'lattice_refine_after',
         'lattice_nonlinear_queries', 'replica_promotions', 'replica_best_gain',
         'replica_best_loss', 'replica_best_benefit', 'replica_selected']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / 'results'
    destination.mkdir(exist_ok=True)
    manifest = {'upstream_commit': 'df74cd2d8255b2f68d5c815a88b55238899177ec',
                'upstream_imp_lean_git_blob': 'd8b584876c2ba5b20564326d3bc3bc7dcad2f08f',
                'official_rust_binary_comparison': False,
                'generator_official_seed_parity': False, 'runs': []}
    for group, (prefix, solvers) in GROUPS.items():
        rows = []
        for solver in solvers:
            run = ROOT / 'runs' / (prefix + solver)
            integrity = json.loads((run / 'integrity.json').read_text())
            if integrity['failures'] or integrity['passed'] != integrity['cases']:
                raise ValueError('Unverified run: ' + run.name)
            cases = replay.run_cases(run)
            metrics = replay.run_metrics(run, processes=1)
            source = run / 'src' / 'main.cpp'
            current = ROOT / 'solutions' / solver / 'main.cpp'
            manifest['runs'].append({'group': group, 'run_id': run.name, 'solver': solver,
                                    'source_sha256': digest(source),
                                    'current_source_sha256': digest(current),
                                    'source_matches_current': source.read_bytes() == current.read_bytes(),
                                    'integrity': integrity})
            shutil.copyfile(run / 'result.json', destination / (run.name + '.json'))
            for seed, case in sorted(cases.items()):
                m = metrics[seed]
                row = {'run_id': run.name, 'seed': seed, 'score': case['score'],
                       'T': m['T'], 'E': m['E'], 'requests': m['requests'],
                       'moves_per_request': m['ops_mean'], 'wall_sec': case['execution_time'],
                       'input_sha256': digest(ROOT / 'tools' / 'in' / f'{seed:04d}.txt'),
                       'stdout_sha256': digest(run / 'out' / f'{seed:04d}.txt'),
                       'stderr_sha256': digest(run / 'err' / f'{seed:04d}.txt')}
                row.update({key: m.get('stderr', {}).get(key, '') for key in STATS})
                rows.append(row)
        with (destination / (group + '.csv')).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'runs': len(manifest['runs']),
                      'verified_solver_cases': sum(x['integrity']['passed'] for x in manifest['runs']),
                      'source_mismatches': [x['run_id'] for x in manifest['runs'] if not x['source_matches_current']]}))


if __name__ == '__main__':
    main()
