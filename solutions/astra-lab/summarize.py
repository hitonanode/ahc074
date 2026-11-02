#!/usr/bin/env python3
"""Export paired scores and strict transcript-integrity checks from completed benchmark runs."""
import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--label', required=True)
    ap.add_argument('--seeds', help='Optional START-END (END excluded), e.g. 32-288')
    ap.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'results')
    args = ap.parse_args()
    selected = None
    if args.seeds:
        start, end = map(int, args.seeds.split('-'))
        selected = set(range(start, end))
    args.out.mkdir(parents=True, exist_ok=True)
    arms, rows, problems = [], [], []
    for run in args.runs:
        path = ROOT / 'runs' / run
        meta = json.loads((path / 'meta.json').read_text())
        input_dir = Path(meta.get('input_directory', ROOT / 'tools' / 'in'))
        result = json.loads((path / 'result.json').read_text())
        metrics = json.loads((path / 'metrics.json').read_text())['cases']
        arm = {'run': run, 'comment': meta.get('comment'), 'cases': {}, 'metrics': {},
               'status': meta.get('status'), 'compile_command': meta.get('compile_command'),
               'research_settings': meta.get('research_settings'),
               'source_sha256': {str(p.relative_to(path)): digest(p) for p in (path / 'src').rglob('*.cpp')}}
        for case in result['cases']:
            s = case['seed']
            if selected is not None and s not in selected:
                continue
            metric = metrics.get(str(s), metrics.get(f'{s:04d}', {}))
            err = path / 'err' / f'{s:04d}.txt'
            out = path / 'out' / f'{s:04d}.txt'
            scores = re.findall(r'(?m)^\s*Score\s*=\s*(\d+)\s*$', err.read_text())
            ok = (case['score'] > 0 and scores and int(scores[-1]) == case['score']
                  and metric.get('score') == case['score'] and not metric.get('error')
                  and metric.get('requests') == 1024)
            if not ok: problems.append({'run': run, 'seed': s, 'reason': 'score/transcript/replay disagreement'})
            arm['cases'][s] = case['score']
            arm['metrics'][s] = metric
            row = {'run': run, 'case': s, 'input_sha256': digest(input_dir / f'{s:04d}.txt'),
                   'score': case['score'], 'E': metric.get('E'), 'T': metric.get('T'),
                   'moves_per_query': metric.get('T', 0) / 1024,
                   'wall_seconds': case['execution_time'], 'transcript_ok': bool(ok),
                   'stdout_sha256': digest(out), 'stderr_sha256': digest(err)}
            for k in ['gobj_after', 'map_iters', 'map_end_sec', 'anneal_iters', 'climb_iters',
                      'generic_moves', 'fast_requests', 'helper_papers', 'req_sec', 'end_sec',
                      'generic_edges', 'generic_extra_hidden', 'overlap_candidates', 'overlap_selected',
                      'joint_matched', 'joint_repairs', 'joint_window_accepts', 'joint_pair_accepts',
                      'rule_changes', 'rule_nonpair', 'rules_end_sec']:
                row[k] = metric.get('stderr', {}).get(k)
            for k, value in metric.get('stderr', {}).items():
                if k.startswith(('cap_', 'model_', 'stationary_', 'rule_')):
                    row[k] = value
            rows.append(row)
        arms.append(arm)
    base = arms[0]['cases']
    summary = []
    for arm in arms:
        common = sorted(set(base) & set(arm['cases']))
        valid = [s for s in common if base[s] > 0 and arm['cases'][s] > 0]
        diffs = [100 * math.log(arm['cases'][s] / base[s]) for s in valid]
        absdiff = [(arm['cases'][s] - base[s]) / 1024 for s in valid]
        summary.append({'run': arm['run'], 'cases': len(common), 'valid_pairs': len(valid),
                        'mean_score': statistics.mean(arm['cases'].values()),
                        'mean_moves_per_query': statistics.mean(m.get('T', 0) / 1024 for m in arm['metrics'].values()),
                        'mean_errors': statistics.mean(m.get('E', 0) for m in arm['metrics'].values()),
                        'mean_log_ratio_percent': statistics.mean(diffs),
                        'se_log_ratio_percent': statistics.stdev(diffs) / math.sqrt(len(diffs)) if len(diffs) > 1 else None,
                        'mean_delta_per_query': statistics.mean(absdiff),
                        'se_delta_per_query': statistics.stdev(absdiff) / math.sqrt(len(absdiff)) if len(absdiff) > 1 else None,
                        'wins': sum(d < 0 for d in diffs), 'ties': sum(d == 0 for d in diffs),
                        'losses': sum(d > 0 for d in diffs)})
    for row in rows:
        b = base.get(row['case'], 0)
        row['delta_moves_per_query'] = (row['score'] - b) / 1024 if b else None
        row['log_ratio_percent'] = 100 * math.log(row['score'] / b) if b and row['score'] else None
    with open(args.out / f'{args.label}.csv', 'w', newline='') as f:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    report = {'label': args.label, 'baseline_run': args.runs[0], 'transcript_problems': problems,
              'selected_seeds': args.seeds,
              'summary': summary,
              'runs': [{k: v for k, v in arm.items() if k not in ('cases', 'metrics')} for arm in arms]}
    (args.out / f'{args.label}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': summary, 'transcript_problems': problems}, ensure_ascii=False, indent=2))
    if problems: raise SystemExit('Do not use this comparison for adoption: transcript integrity failed.')

if __name__ == '__main__':
    main()
