#!/usr/bin/env python3
"""Reproducible fixed-work screen, followed by full independent output checks."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOLVERS = ['imp-lean', 'frontier-lattice', 'frontier-replica', 'frontier-replica-one']
CONTROLS = dict(MAP_ITERS='12000', GOPT_STEPS='3000', ANNEAL_ITERS='6000000',
                CLIMB_ITERS='30000', LATTICE_ITERS='100000')


def main():
    before = set((ROOT / 'runs').iterdir())
    env = os.environ.copy()
    env.update(CONTROLS)
    command = [sys.executable, str(HERE / 'compare.py'), '--compare',
               *['solutions/' + name for name in SOLVERS], '--seeds', '5020-5084',
               '--threads', '4', '--no-record', '-c',
               'frontier: common fixed design work; lattice and duplicate diagnostic; atomic logs']
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    runs = sorted(p for p in (ROOT / 'runs').iterdir() if p not in before and p.is_dir())
    run_by_solver = {name: next(p.name for p in runs if p.name.endswith('_' + name)) for name in SOLVERS}
    manifest = {'controls': CONTROLS, 'seed_range_exclusive': [5020, 5084], 'threads': 4,
                'solvers': SOLVERS, 'runs': run_by_solver, 'command': command}
    (HERE / 'controlled-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run([sys.executable, str(HERE / 'verify_integrity.py'),
                    *[run_by_solver[name] for name in SOLVERS]], cwd=ROOT, check=True)
    comparisons = [('imp-lean', name) for name in SOLVERS[1:]] + [('frontier-replica', 'frontier-replica-one')]
    for baseline, candidate in comparisons:
        subprocess.run([sys.executable, str(HERE / 'summarize_compare.py'),
                        run_by_solver[baseline], run_by_solver[candidate], '--json',
                        str(HERE / ('controlled-' + baseline + '-vs-' + candidate + '.json')),
                        '--stat', 'lattice_accepted', '--stat', 'lattice_nonlinear_windows',
                        '--stat', 'lattice_valid_trials', '--stat', 'lattice_refine_before',
                        '--stat', 'lattice_refine_after', '--stat', 'replica_promotions',
                        '--stat', 'replica_best_gain', '--stat', 'replica_best_loss',
                        '--stat', 'replica_best_benefit', '--stat', 'replica_selected'],
                       cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
