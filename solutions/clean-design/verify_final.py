"""Check refactoring after the ablation; the removed switch has one expected log change."""
import difflib, fcntl, hashlib, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = Path('/home/sato/ahc074/runs')
ABLATION = RUNS / '20261105-144520_clean-design-nogeneric'
FINAL = RUNS / '20261105-144520_clean-design'

def stable(text):
    return '\n'.join(line for line in text.splitlines()
                     if not re.match(r'^\w*sec\s*=', line))

with (RUNS / '.lock').open() as lock:
    fcntl.flock(lock, fcntl.LOCK_SH)
    result = {'ablation': ABLATION.name, 'final': FINAL.name, 'n': 200,
              'stdout_identical': 0, 'stderr_nontime_identical': 0,
              'stderr_expected_as_screen_change_only': 0, 'unexpected': []}
    for seed in range(200):
        name = f'{seed:04d}.txt'
        result['stdout_identical'] += (ABLATION / 'out' / name).read_bytes() == (FINAL / 'out' / name).read_bytes()
        a = stable((ABLATION / 'err' / name).read_text())
        b = stable((FINAL / 'err' / name).read_text())
        result['stderr_nontime_identical'] += a == b
        expected = a.replace('as_screen = 1\n', 'as_screen = 0\n')
        result['stderr_expected_as_screen_change_only'] += expected == b
        if expected != b:
            result['unexpected'].append({'seed': seed, 'diff': list(difflib.unified_diff(
                expected.splitlines(), b.splitlines()))[:40]})
    source = (HERE / 'main.cpp').read_bytes()
    result['source_matches_run'] = source == (FINAL / 'src' / 'main.cpp').read_bytes()
    result['source_matches_build'] = hashlib.sha256(source).hexdigest() == json.loads(
        (HERE / 'build-results.json').read_text())['sha256']
    (HERE / 'final-identity-200.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    assert result['stdout_identical'] == 200
    assert result['stderr_expected_as_screen_change_only'] == 200
    assert result['source_matches_run'] and result['source_matches_build']
