"""ソース、4ビルド、保存設計、2000件の出力一致を照合する。外部ロック下で実行する。"""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('base_run');p.add_argument('run');a=p.parse_args()
here=Path(__file__).resolve().parent
study=here.parent/'argon-des-design-speed'
root=Path('/home/sato/ahc074/runs')
run=root/a.run;base_run=root/a.base_run
source=(here/'main.cpp').read_text()
base=(here.parent/'argon-des-perf-stratacut/main.cpp').read_text()
assert source==(run/'src/main.cpp').read_text()
assert base==(base_run/'src/main.cpp').read_text()
sha=hashlib.sha256(source.encode()).hexdigest()
builds=json.loads((here/'build-results.json').read_text())
assert builds['sha256']==sha and builds['temporary_binaries_removed']
assert len(builds['results'])==4 and all(r['exit']==0 and r['warnings']==0 for r in builds['results'])
for path in here.iterdir():
    if path.is_file():
        with path.open('rb') as f: assert f.read(4)!=b'\x7fELF',path
def unchanged(s):
    for first,last in [
        ('    void build_tables() {','    // The orders (indices of perms)'),
        ('// ==== Handle perforation ====','// ==== Design state:'),
        ('    // ==== design_papers: handle perforation ====','#ifdef LOCAL_BENCH\n// ==== Saving and loading'),
    ]:
        lo=s.index(first);hi=s.index(last,lo);s=s[:lo]+s[hi:]
    return s
assert unchanged(source)==unchanged(base)
assert [l.strip() for l in source.splitlines() if l.strip().startswith('// ====')]==[
    l.strip() for l in base.splitlines() if l.strip().startswith('// ====')]
assert source[:source.index('// ==== Common:')]==base[:base.index('// ==== Common:')]
identity=json.loads((study/'packed2000-identity.json').read_text())
assert identity['base']==a.base_run and identity['candidate']==a.run
assert identity['n']==identity['stdout_identical']==identity['stderr_identical']==2000
summary=json.loads((study/'packed2000.json').read_text())
b,c=summary
assert b['run']==a.base_run and c['run']==a.run and b['n']==c['n']==2000
assert c['score']['mean']==c['score']['se']==0 and c['wtl']==[0,2000,0]
assert c['judge_delta']['mean']<=-.005 and c['judge_delta']['p99_difference']<=.010
def payload(path):
    return '\n'.join(l for l in path.read_text().split('stderr ',1)[0].splitlines()
                     if not l.startswith(('end_ticks ','end_sec ')))
for name in [a.base_run,a.run]:
    r=root/name
    cases=json.loads((r/'metrics.json').read_text())['cases']
    assert len(cases)==2000
    assert all(x['score']>0 and x['stderr']['self_wrong']==0 and x['stderr']['op_label_errors']==0 for x in cases.values())
    assert len(list((r/'design').iterdir()))==2000
    assert json.loads((r/'meta.json').read_text())['record']
for path in (run/'design').iterdir():
    assert payload(path)==payload(base_run/'design'/path.name)
result=dict(run=a.run,base_run=a.base_run,sha256=sha,cases=2000,designs=2000,builds=4,warnings=0,
            wa=0,self_wrong=0,op_label_errors=0,stdout_identical=2000,non_timing_stderr_identical=2000,
            design_payloads_identical=True,other_code_identical=True,temporary_binaries_removed=True,
            judge_mean_delta=c['judge_delta']['mean'],judge_p99_delta=c['judge_delta']['p99_difference'])
(here/'final-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
