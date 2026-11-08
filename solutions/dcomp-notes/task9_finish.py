"""Recorded final comparison, followed by an unseen-list confirmation."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
N=Path(__file__).resolve().parent;ROOT=N.parents[1];R=Path('/home/sato/ahc074/runs')
PY='/home/sato/ahc074/.venv/bin/python'
def locked(script,args,log):
    with (N/log).open('w') as out:
        subprocess.run(['flock','-x',str(R/'.lock'),'nice','-n','10',PY,str(N/script),*args],
                       cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
def run(args,log):
    with (N/log).open('w') as out:
        subprocess.run([PY,str(N/'run.py'),*args],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
    ids=re.findall(r'\[pahcer_run\] run-id: (\S+)',(N/log).read_text())
    for rid in ids:assert json.loads((R/rid/'meta.json').read_text())['status']=='ok'
    return ids
# Every prerequisite is independent of held-out score tuning.
for fn,n in [('t9-repeat-nine-identity.json',500),('t9-ten-late-identity.json',500),
             ('t9-gcc-native-dcomp-nine-fast-identity.json',200),
             ('t9-clang-native-dcomp-nine-fast-identity.json',200)]:
    x=json.loads((N/fn).read_text());assert x['n']>=n and not x['different']
x=json.loads((N/'t9-candidate-check.json').read_text());assert x['first_nine_exact_records']>=1800
source=ROOT/'solutions/dcomp-ten-fast/main.cpp';sha=hashlib.sha256(source.read_bytes()).hexdigest()
audit=json.loads((N/'t9-source-audit.json').read_text());assert sha==audit['ten_fast_sha256']
freeze={'candidate':'dcomp-ten-fast','sha256':sha,'bytes':source.stat().st_size,
        'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        'settings':'frozen ten-late + exact sparse relation costs / sorted valid bitset',
        'tuning_seeds':[0,500]}
fp=N/'FROZEN9.json';assert not fp.exists();fp.write_text(json.dumps(freeze,indent=2)+'\n')
ids=run(['--compare','solutions/argon-des-perf-latew105','solutions/legal-tie-fix',
         'solutions/dcomp-nine','solutions/dcomp-ten-fast','--seeds','0-2000','--save-design',
         '-c','Task9 frozen final: exact window speedup pays for candidate ten; recorded 2000'],
        't9-final-normal.log')
assert len(ids)==4 and ids[-1].endswith('_dcomp-ten-fast')
manifest={'frozen':freeze,'final_normal':ids};(N/'t9-final-runs.json').write_text(json.dumps(manifest,indent=2)+'\n')
locked('task9_final_stats.py',ids+['--output',str(N/'t9-final-stats.json')],'t9-final-stats.log')
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
rep=run(['solutions/legal-tie-fast','--design-from',ids[-1],'--orders','8','--seeds','500-1000',
         '-c','Task9 frozen ten-fast unseen lists 1-7, same legal-tie-fast requests'],
        't9-final-replay.log')
assert len(rep)==1
manifest['replay']=rep[0];manifest['replay_reference']='20261108-115455_legal-tie-fast'
(N/'t9-final-runs.json').write_text(json.dumps(manifest,indent=2)+'\n')
locked('metrics.py',[manifest['replay_reference'],rep[0],'--seeds','500-1000','--output',str(N/'t9-final-replay-metrics.json')],
       't9-final-replay-metrics.log')
normal={int(c['seed']):c for c in json.loads((R/ids[-1]/'result.json').read_text())['cases']}
cases=json.loads((R/rep[0]/'result.json').read_text())['cases'];assert len(cases)==500
assert all(len(c['order_scores'])==8 and c['order_scores'][0]==normal[int(c['seed'])]['score'] for c in cases)
manifest['replay_real_list_identical']=500
(N/'t9-final-runs.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
