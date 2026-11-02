#!/usr/bin/env python3
"""完了した64設計の比較表・出典ハッシュを保存する。実験は再実行しない。"""
from pathlib import Path
import csv,hashlib,json,math

ROOT=Path(__file__).resolve().parent
labels=['baseline','oracle255-t1','expanded128-k2']
data={}
for label in labels:
    cases={}
    for seed in range(24,88):
        path=ROOT/'results'/label/f'{seed:04d}.jsonl'
        rows=[json.loads(x) for x in path.read_text().splitlines()]
        assert len(rows)==5,(label,seed,len(rows))
        assert [r['sequence'] for r in rows[1:]]==list(range(4))
        assert all(r['steps']==1024 and r['wrong']==r['illegal']==r['oracle_bad']==0 for r in rows[1:])
        cases[seed]={'hash':rows[0]['design_hash'],'G':rows[0]['G']}
        for key in ['total','generic','lift','old_top','old_filler','dig_d','filler','fix']:
            cases[seed][key]=sum(r[key] for r in rows[1:])
        assert cases[seed]['total']==sum(cases[seed][k] for k in ['generic','lift','old_top','old_filler','dig_d','filler','fix'])
    data[label]=cases
rows=[]
for seed in range(24,88):
    b,o,e=[data[label][seed] for label in labels]
    assert b['hash']==o['hash']==e['hash'] and b['G']==o['G']==e['G']
    row={'seed':seed,'G':b['G'],'design_hash':b['hash'],
         'baseline_moves_4seq':b['total'],'oracle255_moves_4seq':o['total'],'expanded128_moves_4seq':e['total'],
         'oracle255_log_ratio_percent':100*math.log(o['total']/b['total']),
         'expanded128_log_ratio_percent':100*math.log(e['total']/b['total'])}
    for label,c in [('oracle255',o),('expanded128',e)]:
        for key in ['total','generic','lift','old_top','old_filler','dig_d','filler','fix']:
            row[f'{label}_{key}_delta_per_request']=(c[key]-b[key])/4096
    rows.append(row)
out=ROOT/'results/per_case.csv'
with out.open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
sources=[ROOT.parent/'as6-cap38p0/main.cpp']+[ROOT/x for x in [
    'research.cpp','diagnostic.cpp','fast.cpp','oracle.inc','harness.inc','expand.inc',
    'build_research.py','build_diagnostic.py','build_fast.py','run_research.py','summarize.py',
    'choice_audit.cpp','build_choice_audit.py']]
manifest={'cases':64,'sequences_per_case':4,'requests_per_sequence':1024,'seeds':[24,87],
          'build_flags':['-std=c++23','-O2','-DCLOCK_SCALE=1.1'],
          'sources':{str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
          'data':{},'checks':{'all_designs_equal':True,'wrong':0,'illegal':0,'oracle_bad':0}}
for label in labels:
    manifest['data'][label]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'results'/label).glob('*.jsonl'))}
(ROOT/'results/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('64 designs × 4 sequences verified; results/per_case.csv and results/manifest.json written.')
