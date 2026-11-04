"""Compare recorded arms; never executes a solution or tester."""
import argparse
import json
import math
import re
import statistics as st
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("log", type=Path)
ap.add_argument("--arm", type=int, default=1)
args = ap.parse_args()
runs = Path('/home/sato/ahc074/runs')
ids = re.findall(r'\[pahcer_run\] run-id: (\S+)', args.log.read_text())
assert len(ids) > args.arm, ids
ids = [ids[0], ids[args.arm]]
records = []
all_logs = []
annotations = []
for rid in ids:
    root = runs / rid
    meta = json.loads((root / 'meta.json').read_text())
    assert meta['status'] == 'ok', (rid, meta['status'])
    expected = (meta['seeds'][1] - meta['seeds'][0]) * (meta.get('design_from') or {}).get('orders', 1)
    logs = sorted((root / 'err').glob('*.txt'))
    logs += sorted(root.glob('orders/*/err/*.txt'))
    metrics = {}
    by_file = {}
    ann = {}
    for path in logs:
        content = path.read_text()
        vals = dict((m[0], float(m[1])) for m in re.findall(
            r'^([a-zA-Z_][a-zA-Z_0-9]*) = (-?[\d.eE+]+)$', content, re.M))
        by_file[str(path.relative_to(root))] = vals
        ann[str(path.relative_to(root))] = '\n'.join(line for line in content.splitlines() if line.startswith('@'))
        for key, value in vals.items():
            metrics.setdefault(key, []).append(value)
    out = {str(p.relative_to(root)): p.read_bytes() for p in root.glob('out/*.txt')}
    out.update({str(p.relative_to(root)): p.read_bytes() for p in root.glob('orders/*/out/*.txt')})
    assert len(logs) == len(out) == expected, (rid, expected, len(logs), len(out))
    records.append((out, metrics))
    all_logs.append(by_file)
    annotations.append(ann)

o0, m0 = records[0]
o1, m1 = records[1]
shared = sorted(set(o0) & set(o1))
different = [key for key in shared if o0[key] != o1[key]]
means = [{k: st.mean(v) for k, v in m.items()} for _, m in records]
paired_log = [math.log(b/a) for a, b in zip(m0['req_sec'], m1['req_sec'])]
by_seed = {}
for path, vals in all_logs[0].items():
    other = all_logs[1].get(path)
    if other is not None:
        by_seed.setdefault(Path(path).stem, []).append((vals['req_sec'], other['req_sec']))
seed_means = [(st.mean(a for a,b in pairs), st.mean(b for a,b in pairs)) for pairs in by_seed.values()]
ratio = means[1]['req_sec'] / means[0]['req_sec']
ratio_se = (st.stdev(b - ratio*a for a,b in seed_means) / math.sqrt(len(seed_means))
            / st.mean(a for a,b in seed_means)) if len(seed_means) > 1 else 0
report = {
    'runs': ids,
    'cases': len(shared),
    'byte_identical': len(shared) - len(different),
    'different_count': len(different),
    'missing': sorted(set(o0) ^ set(o1)),
    'mean_req_sec': [m['req_sec'] for m in means],
    'req_ratio': ratio,
    'req_ratio_se_by_seed': ratio_se,
    'paired_req_log_mean': st.mean(paired_log),
    'paired_req_log_se': st.stdev(paired_log)/math.sqrt(len(paired_log)) if len(paired_log)>1 else 0,
    'wa': [sum(x == 0 for x in m.get('Score', [])) for _, m in records],
    'self_wrong_max': [max(m.get('self_wrong', [-1])) for _, m in records],
    'op_label_errors_max': [max(m.get('op_label_errors', [-1])) for _, m in records],
    'annotation_differences': sum(annotations[0][k] != annotations[1].get(k) for k in annotations[0]),
    'candidate_counter_differences': {
        metric: sum(v.get(metric) != all_logs[1].get(k, {}).get(metric) for k, v in all_logs[0].items())
        for metric in ['eject_pairs', 'eject_trials', 'eject_accepts', 'triple_trials', 'triple_repairs',
                       'triple_accepts', 'rewrite_trials', 'rewrite_accepts', 'ns_one_trials',
                       'ns_one_accepts', 'ns_rounds', 'neutral_total', 'neutral_accepted']},
    'end_sec': [{str(t): sum(v > t for v in m['end_sec']) for t in [1.8, 1.9, 2.0]} | {'mean': st.mean(m['end_sec']), 'max': max(m['end_sec'])} for _, m in records],
    'outside_load': [json.loads((runs/rid/'meta.json').read_text()).get('outside_load') for rid in ids],
    'means': means,
}
score_logs = {}
for path, vals in all_logs[0].items():
    other = all_logs[1].get(path)
    if other and vals['Score'] and other['Score']:
        score_logs.setdefault(Path(path).stem, []).append(math.log(other['Score'] / vals['Score']))
score_means = [st.mean(v) for v in score_logs.values()]
report['log_score_pct'] = 100 * st.mean(score_means)
report['log_score_se_pct'] = 100 * st.stdev(score_means) / math.sqrt(len(score_means)) if len(score_means) > 1 else 0
report['win_tie_loss_seeds'] = [sum(x < 0 for x in score_means), sum(x == 0 for x in score_means), sum(x > 0 for x in score_means)]
report['win_tie_loss_cases'] = [sum(x < 0 for v in score_logs.values() for x in v), sum(x == 0 for v in score_logs.values() for x in v), sum(x > 0 for v in score_logs.values() for x in v)]
target = args.log.with_suffix('.json') if args.arm == 1 else args.log.with_name(args.log.stem + f'-arm{args.arm}.json')
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'means'}, indent=2))
assert not report['missing']
assert report['wa'] == [0, 0]
assert report['self_wrong_max'] == report['op_label_errors_max'] == [0, 0]

ends = ['map_end_sec', 'anneal_end_sec', 'climb_end_sec', 'match_end_sec', 'perforation_end_sec', 'helper_end_sec', 'end_sec']
stages = ['map', 'anneal', 'climb', 'match', 'perforation', 'helper', 'requests_and_output']
report['stage_times'] = {}
for i, (end, stage) in enumerate(zip(ends, stages)):
    vals = [m[end] - (m[ends[i-1]] if i else 0) for m in means]
    report['stage_times'][stage] = {'seconds': vals, 'ratio': vals[1]/vals[0]}
    print(stage, vals, 'ratio', vals[1]/vals[0])
report['cumulative_times'] = {k: [m[k] for m in means] for k in ends}
for i, stage in enumerate(stages):
    pairs = []
    for key, v in all_logs[0].items():
        w = all_logs[1][key]
        pairs.append(tuple(x[ends[i]] - (x[ends[i-1]] if i else 0) for x in (v,w)))
    ratio = report['stage_times'][stage]['ratio']
    report['stage_times'][stage]['ratio_se'] = st.stdev(b-ratio*a for a,b in pairs)/math.sqrt(len(pairs))/st.mean(a for a,b in pairs)
vals = [m['helper_end_sec'] - m['map_end_sec'] for m in means]
report['post_map_design'] = {'seconds': vals, 'ratio': vals[1]/vals[0], 'saved_seconds': vals[0]-vals[1]}
report['judge_model'] = [1.04*m['helper_end_sec'] + 1.35*m['req_sec'] for m in means]

report['non_time_metric_differences'] = {
    metric: sum(v.get(metric) != all_logs[1].get(k, {}).get(metric) for k, v in all_logs[0].items())
    for metric in means[0] if not metric.endswith('_sec') and not metric.startswith('cfprof_')}
report['different_outputs'] = different
report['profile'] = {k: v for k,v in means[1].items() if k.startswith('af_')}
target.write_text(json.dumps(report, indent=2) + '\n')
for k,v in report['profile'].items():
    if k.endswith('_sec'): print(k, v)
print('Non-time differences:', {k:v for k,v in report['non_time_metric_differences'].items() if v})
