#!/usr/bin/env python3
"""Verify saved replay scores and exact evaluator output hashes without rerunning solvers."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import replay

def verify(arg):
    path = replay.resolve_run(arg)
    cases = replay.run_cases(path)
    metrics = replay.run_metrics(path, processes=1)
    bad = []
    for seed, case in cases.items():
        output = (path / 'out' / f'{seed:04d}.txt').read_bytes()
        err_bytes = (path / 'err' / f'{seed:04d}.txt').read_bytes()
        err = err_bytes.decode()
        checks = []
        if case.get('log_storage') == 'atomic-from-pipes':
            for name, data in [('stdout', output), ('stderr', err_bytes)]:
                if case.get(name + '_bytes') != len(data):
                    checks.append(name + ' captured length')
                if case.get(name + '_sha256') != hashlib.sha256(data).hexdigest():
                    checks.append(name + ' captured hash')
        size = re.search(r'^tester_relay_bytes = (\d+)$', err, re.M)
        fnv = re.search(r'^tester_relay_fnv64 = ([0-9a-fA-F]+)$', err, re.M)
        score = re.search(r'^Score = (\d+)$', err, re.M)
        value = 14695981039346656037
        for byte in output:
            value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
        if not size or int(size[1]) != len(output): checks.append('output length')
        if not fnv or int(fnv[1], 16) != value: checks.append('output hash')
        if not score or int(score[1]) != case['score']: checks.append('stderr score')
        inp = replay.load_input(seed)
        parsed = replay.parse_output(inp, output.decode())
        replayed = replay.replay(inp, parsed, check=True)
        if replayed.error or replayed.score != case['score']:
            checks.append('legal replay: ' + str(replayed.error))
        m = metrics[seed]
        if m['requests'] != 1024: checks.append('request count')
        if m['score'] != case['score']: checks.append('replay score')
        if m['T'] + 384 * m['E'] != case['score']: checks.append('E/T score identity')
        if checks: bad.append({'seed': seed, 'failures': checks})
    report = {'run_id': path.name, 'cases': len(cases), 'passed': len(cases) - len(bad), 'failures': bad}
    (path / 'integrity.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return not bad

if __name__ == '__main__':
    results = [verify(arg) for arg in sys.argv[1:]]
    raise SystemExit(0 if all(results) else 1)
