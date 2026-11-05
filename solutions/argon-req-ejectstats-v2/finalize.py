"""Final verification from saved artifacts, never executing the solver or tester."""
from pathlib import Path
import json
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
root = Path('/home/sato/ahc074/runs')
scratch = Path('/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/4b08d16a-e458-4ef7-a878-a32403e05bc1/scratchpad/argon')
base_text = (scratch/'BASE.md').read_text()
assert '**Current base (SOTA): `solutions/argon-req-filterblocks-v2`**' in base_text, 'Base changed: port before adopting.'
(here/'base-at-final.txt').write_text(base_text)
for label, log, orders in [('fixed','fixed-screen.log',2), ('normal','normal-final.log',1)]:
    with (here/(label+'-analysis.log')).open('w') as out:
        subprocess.run([sys.executable, str(here/'validate.py'), str(here/log), '--label', label,
                        '--seeds','2000','--orders',str(orders)], stdout=out, stderr=subprocess.STDOUT, check=True)
with (here/'trace-validation.log').open('w') as out:
    subprocess.run([sys.executable,str(here/'check_trace.py')],stdout=out,stderr=subprocess.STDOUT,check=True)
assert 'All four builds passed with no warnings.' in (here/'builds.log').read_text()
fixed = json.loads((here/'fixed-details.json').read_text())
normal = json.loads((here/'normal-details.json').read_text())
f = json.loads((here/'fixed-results.json').read_text())[fixed['runs'][1]]
n = json.loads((here/'normal-results.json').read_text())[normal['runs'][1]]
for side in range(2):
    a, b = [root/name for name in [fixed['runs'][side],normal['runs'][side]]]
    assert len(list((b/'design').iterdir())) == 2000
    for seed in range(2000):
        assert (a/'out'/f'{seed:04d}.txt').read_bytes() == (b/'out'/f'{seed:04d}.txt').read_bytes(), (side,seed)
before = Path('solutions/argon-req-filterblocks-v2/main.cpp').read_text()
after = (here/'main.cpp').read_text()
process = '    // ==== Request processing (process) ===='
emergency = '// ==== Emergency design ===='
stats = '    // ==== main: statistics ===='
assert before[:before.index(process)] == after[:after.index(process)]
assert before[before.index(emergency):before.index(stats)] == after[after.index(emergency):after.index(stats)]
assert re.findall(r'^\s*// ====.*$',before,re.M) == re.findall(r'^\s*// ====.*$',after,re.M)
print('Only request processing and final statistics changed; all section names retained.',flush=True)
print('Both arms: normal outputs equal fixed-design order 0 on all 2000 seeds; 2000 saved designs each.',flush=True)
print('Four warning-free builds and heavy trace consistency confirmed.',flush=True)
rate = -f['score_log_pct']/n['judge_mean_delta'] if n['judge_mean_delta']>0 else None
load = {}
for label, info in [('fixed',fixed),('normal',normal)]:
    meta = json.loads((root/info['runs'][1]/'meta.json').read_text())
    assert meta['record'] == (label == 'normal')
    load[label] = [meta['outside_load']] + [e['outside_load'] for e in meta.get('extensions',[])]
    assert all(x['mean_cores'] <= .5 and x['max_cores'] <= 3 for x in load[label]), load[label]
result = {'fixed':f,'normal':n,'efficiency_pct_per_judge_sec':rate,
          'paired_normal':normal['paired_times'],'local_gain':fixed['local_gain'],'outside_load':load}
(here/'adoption.json').write_text(json.dumps(result,indent=2)+'\n')
print('fixed',f['score_log_pct'],'+-',f['se_pct'],f['wtl'],'req ratio',f['req_ratio'],flush=True)
print('normal',n['score_log_pct'],'+-',n['se_pct'],n['wtl'],'req ratio',n['req_ratio'],flush=True)
print('judge delta',n['judge_mean_delta'],'p99 delta',n['judge_p99_delta'],'efficiency',rate,flush=True)
print('diagnostics',fixed['local_gain'],flush=True)
assert -f['score_log_pct'] >= .005 and f['score_log_pct']+2*f['se_pct']<0
assert n['score_log_pct'] < 0
assert n['judge_mean_delta'] <= .033
assert n['judge_p99_delta'] <= max(0,n['judge_mean_delta'])+.010
assert rate is None or rate >= .6, rate
assert n['WA'] == f['WA'] == 0
print('All adoption criteria passed on the current base.',flush=True)
