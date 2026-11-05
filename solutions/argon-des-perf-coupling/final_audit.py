"""Audit saved results and every printed product; never execute the solution."""
import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

study = Path(__file__).resolve().parent
root = study.parent
runs = Path('/home/sato/ahc074/runs')
p = argparse.ArgumentParser()
p.add_argument('directory')
p.add_argument('base_run')
p.add_argument('candidate_run')
p.add_argument('--base', default='argon-des-perf-latew105')
p.add_argument('--free', type=float, default=.015)
a = p.parse_args()
here = Path(a.directory).resolve()

def mean_se(x):
    return dict(mean=statistics.mean(x), se=statistics.stdev(x)/math.sqrt(len(x)))

def quantile(x, fraction):
    x = sorted(x)
    pos = fraction * (len(x)-1)
    i = int(pos)
    return x[i] + (x[min(i+1, len(x)-1)]-x[i]) * (pos-i)

def read_design(path):
    result = {}
    vectors = {'permutation','A','edge','polarity','papers','columns','ded','handle'}
    for line in path.read_text().splitlines():
        key, *v = line.split()
        if key == 'stderr': break
        if key in vectors:
            assert int(v[0]) == len(v)-1
            result[key] = list(map(int,v[1:]))
        elif key in {'M','G','H','emergency'}:
            result[key] = int(v[0])
    return result

source = (here/'main.cpp').read_text()
base_source = (root/a.base/'main.cpp').read_text()
assert (runs/a.candidate_run/'src/main.cpp').read_text() == source
assert (runs/a.base_run/'src/main.cpp').read_text() == base_source
sha = hashlib.sha256(source.encode()).hexdigest()
build = json.loads((here/'build-results.json').read_text())
assert build['sha256'] == sha
assert len(build['results']) == 4 and all(r['exit'] == 0 and r['warnings'] == 0 for r in build['results'])
assert build['temporary_binaries_removed']

restored = source.replace('//   design_papers: alternating perforation and reassignment\n', '')
a1 = restored.index('// ==== Handle perforation ====')
a2 = restored.index('// ==== Design state:', a1)
b1 = base_source.index('// ==== Handle perforation ====')
b2 = base_source.index('// ==== Design state:', b1)
restored = restored[:a1] + base_source[b1:b2] + restored[a2:]
a1 = restored.index('    // ==== design_papers: alternating perforation and reassignment ====')
a2 = restored.index('    return state;', a1)
restored = restored[:a1] + restored[a2:]
assert [l for l in restored.splitlines() if l.strip()] == [l for l in base_source.splitlines() if l.strip()], 'Changes outside the perforation and its new stage'
markers = re.findall(r'^\s*// ==== (.*?) ====$', source, re.M)
base_markers = re.findall(r'^\s*// ==== (.*?) ====$', base_source, re.M)
assert [m for m in markers if m != 'design_papers: alternating perforation and reassignment'] == base_markers
assert markers.count('design_papers: alternating perforation and reassignment') == 1
toc = [l[5:] for l in source.splitlines() if l.startswith('//   ')]
assert toc == markers, 'Table of contents mismatch'

metrics = [json.loads((runs/r/'metrics.json').read_text())['cases'] for r in [a.base_run,a.candidate_run]]
expected = {str(i) for i in range(2000)}
assert all(set(m) == expected for m in metrics)
design_metrics = []
for k in metrics[0]['0']['stderr']:
    if '_sec' in k or '_ms' in k: continue
    if k.startswith(('gobj_','gopt_','map_','anneal_','colswap_','replace_','climb_','proxy_',
                     'match_','model_','perf_','perforation_','d2_rematch_','d2_model_','d2_filler_','d2_extra_')) or k == 'cap_window':
        design_metrics.append(k)
for seed in expected:
    b,c = [m[seed] for m in metrics]
    assert b['score'] > 0 and c['score'] > 0
    for row in [b,c]:
        assert row['stderr']['self_wrong'] == row['stderr']['op_label_errors'] == 0
    assert c['stderr']['d2_rematch_iterations'] == 1
    assert all(b['stderr'][k] == c['stderr'][k] for k in design_metrics), seed

design_names = [{f.name for f in (runs/r/'design').glob('*.txt')} for r in [a.base_run,a.candidate_run]]
assert len(design_names[0]) == 2000 and design_names[0] == design_names[1]
count_changed = 0
fixed_fields = ['M','G','H','emergency','permutation','A','edge','polarity','columns','handle','ded']
for name in sorted(design_names[0]):
    b,c = [read_design(runs/r/'design'/name) for r in [a.base_run,a.candidate_run]]
    assert all(b[k] == c[k] for k in fixed_fields), name
    assert b['papers'][:14] == c['papers'][:14]
    owners = [[[] for _ in range(192)] for _ in range(2)]
    for arm,d in enumerate([b,c]):
        for target,k in enumerate(d['ded']): owners[arm][k].append(target)

    def printed(d, targets, column):
        mask = (1 << d['G']) - 1
        for j in range(column+1): mask |= 1 << d['handle'][j]
        if len(targets) == 2: mask &= ~(d['A'][targets[0]] ^ d['A'][targets[1]])
        mask |= 1 << 63
        black = d['A'][targets[0]] & mask
        if len(targets) == 2 and (d['A'][targets[0]] ^ d['A'][targets[1]]) >> 63 & 1:
            black &= ~(1 << 63)
        return mask,black

    added = restored_holes = 0
    for k in range(7,192):
        assert len(owners[0][k]) == len(owners[1][k]) in [1,2]
        column = b['columns'][k]
        allowed_extra = sum(1 << b['handle'][j] for j in range(column))
        for d, targets in [(b,owners[0][k]),(c,owners[1][k])]:
            full, black = printed(d, targets, column)
            opaque = d['papers'][2*k]
            extra = full & ~opaque
            assert opaque & ~full == 0 and extra & ~allowed_extra == 0, (name,k)
            assert black & opaque == d['papers'][2*k+1], (name,k)
        changed = b['papers'][2*k] ^ c['papers'][2*k]
        assert not changed & ~allowed_extra
        added += (b['papers'][2*k] & ~c['papers'][2*k]).bit_count()
        restored_holes += (c['papers'][2*k] & ~b['papers'][2*k]).bit_count()
    count_changed += b['papers'] != c['papers']

score = [100*math.log(metrics[1][s]['score']/metrics[0][s]['score']) for s in expected]
summary = []
for run,m in zip([a.base_run,a.candidate_run],metrics):
    judge = [m[s]['stderr']['end_sec']+.04*m[s]['stderr']['helper_end_sec']+.35*m[s]['stderr']['req_sec'] for s in expected]
    summary.append(dict(run=run, judge={**mean_se(judge), 'p99':quantile(judge,.99),
                                     'max':max(judge),'over2':sum(x>2 for x in judge)},
                        metrics={k:statistics.mean(m[s]['stderr'][k] for s in expected)
                                 for k in ['req_sec','helper_end_sec','end_sec']}, values=judge))
delta = mean_se([c-b for b,c in zip(summary[0]['values'],summary[1]['values'])])
delta['p99'] = summary[1]['judge']['p99']-summary[0]['judge']['p99']
for r in summary: del r['values']
score_stats = mean_se(score)
wtl = [sum(metrics[1][s]['score'] < metrics[0][s]['score'] for s in expected),
       sum(metrics[1][s]['score'] == metrics[0][s]['score'] for s in expected),
       sum(metrics[1][s]['score'] > metrics[0][s]['score'] for s in expected)]
load = []
for run in [a.base_run,a.candidate_run]:
    meta = json.loads((runs/run/'meta.json').read_text())
    assert not meta.get('design_from')
    for entry in [meta, *meta.get('extensions',[])]:
        item = entry.get('outside_load')
        if item:
            load.append(item)
            assert item['mean_cores'] <= .5 and item['max_cores'] <= 3, (run,item)
    assert not meta.get('no_record',False)

gain = -score_stats['mean']
criteria = dict(score_2se=gain >= 2*score_stats['se'], practical=gain >= .03,
                free_budget=delta['mean'] <= a.free,
                efficiency=delta['mean'] <= .002 or gain/delta['mean'] >= .6,
                p99=delta['p99'] <= max(0,delta['mean'])+.010)
result = dict(base=a.base, candidate=here.name, source_sha256=sha, n=2000,
              score=score_stats, wtl=wtl, time=summary, judge_delta=delta,
              gain_per_judge_second=gain/delta['mean'] if delta['mean'] > 0 else None,
              changed_designs=count_changed, retained_pre_stage_metrics=design_metrics,
              source_scope_verified=True, physical_papers_verified=2000,
              warning_free_builds=4, outside_load=load, criteria=criteria)
(here/'final-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert all(criteria.values()), criteria
