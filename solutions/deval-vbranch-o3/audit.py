"""Read-only validation of the frozen source, replay, and evaluation records.

Run under flock -x /home/sato/ahc074/runs/.lock. Writes only audit.json here.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
RUNS = Path('/home/sato/ahc074/runs')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen = read(HERE / 'FROZEN.json')
    result = read(HERE / 'final_metrics.json')
    source = (HERE / 'main.cpp').read_text()
    contents = re.findall(r'^//   (.+)$', source.split('#ifndef', 1)[0], re.M)
    sections = re.findall(r'^\s*// ==== (.+) ====$', source, re.M)
    assert contents == sections
    assert sha(HERE / 'main.cpp') == frozen['source_sha256'] == result['source_sha256']
    assert sha(HERE / 'V.json') == frozen['value_model_sha256']
    assert len(source.encode()) <= 520000
    assert '#include <bits/stdc++.h>' not in source

    normal = read(RUNS / result['candidate'] / 'result.json')['cases']
    replay = read(RUNS / result['replay'] / 'result.json')['cases']
    normal_scores = {int(c['seed']): c['score'] for c in normal}
    assert len(normal_scores) == 2000 and min(normal_scores.values()) > 0
    assert {int(c['seed']) for c in replay} == set(range(1000))
    assert all(len(c['order_scores']) == 8 and min(c['order_scores']) > 0 for c in replay)
    mismatches = [int(c['seed']) for c in replay
                  if c['order_scores'][0] != normal_scores[int(c['seed'])]]
    assert not mismatches, ('DesignStore real-order replay differs', mismatches)

    checked_runs = {}
    for run in [result['candidate'], result['replay'], *result['guard']]:
        assert sha(RUNS / run / 'src' / 'main.cpp') == frozen['source_sha256']
        meta = read(RUNS / run / 'meta.json')
        checked_runs[run] = {'compile_command': meta['compile_command'],
                             'source_sha256': frozen['source_sha256']}

    metrics = read(RUNS / result['candidate'] / 'metrics.json')['cases']
    counts = {}
    selected = {}
    for case in metrics.values():
        stderr = case['stderr']
        n, i = int(stderr['dv_candidates']), int(stderr['dv_chosen'])
        counts[n] = counts.get(n, 0) + 1
        selected[i] = selected.get(i, 0) + 1
        assert 0 <= i < n <= 4

    output = {'all_checks_pass': True, 'source_bytes': len(source.encode()),
              'sections': len(sections), 'replayed_real_lists': len(replay),
              'replay_score_mismatches': mismatches,
              'completed_candidate_counts': counts, 'selected_candidate_counts': selected,
              'runs': checked_runs}
    (HERE / 'audit.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({k: v for k, v in output.items() if k != 'runs'}, indent=2))


if __name__ == '__main__':
    main()
