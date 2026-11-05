"""既存の同時比較から時間外れ値と生成コードサイズを調べる。whenidle+flockで起動。"""
import argparse
import json
import statistics
import subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('prefix');a=p.parse_args()
here=Path(__file__).resolve().parent;root=Path('/home/sato/ahc074/runs')
data=[]
for name in [a.base,a.candidate]:
    r=root/name;cases=json.loads((r/'metrics.json').read_text())['cases'];rows={}
    for seed,c in cases.items():
        e=c['stderr'];last=0;phases={}
        for part in ['map','anneal','climb','match','perforation','helper']:
            now=e[part+'_end_sec'];phases[part]=now-last;last=now
        phases['req']=e['req_sec']
        phases['judge']=e['end_sec']+.04*e['helper_end_sec']+.35*e['req_sec']
        phases['mtime']=(r/'out'/f'{int(seed):04d}.txt').stat().st_mtime
        rows[int(seed)]=phases
    data.append(rows)
b,c=data
result={'base':a.base,'candidate':a.candidate,'rows':[
    dict(seed=s,base=b[s],candidate=c[s],delta={k:c[s][k]-b[s][k] for k in b[s] if k!='mtime'}) for s in sorted(b)]}
for key in ['judge','map','anneal','helper','req']:
    top=sorted(result['rows'],key=lambda r:r['delta'][key],reverse=True)[:20]
    print('top delta',key,[(r['seed'],round(r['delta'][key],6)) for r in top])
for label,selector in [('all',lambda r:True),('first500',lambda r:r['seed']<500),('extension',lambda r:r['seed']>=500),
                       ('candidate_tail',lambda r:r['candidate']['judge']>=1.9)]:
    rows=[r for r in result['rows'] if selector(r)]
    print(label,len(rows),{k:round(statistics.mean(r['delta'][k] for r in rows),6) for k in rows[0]['delta']})
symbols=[]
for name in [a.base,a.candidate]:
    out=subprocess.check_output(['nm','-C','-S','--size-sort',str(root/name/'a.out')],text=True)
    (here/(a.prefix+'-'+name.split('_',1)[1]+'-symbols.txt')).write_text(out)
    sym={}
    for line in out.splitlines():
        fields=line.split(maxsplit=3)
        if len(fields)==4 and all(x in '0123456789abcdefABCDEF' for x in fields[1]):
            sym[fields[3]]={'address':fields[0],'size':int(fields[1],16)}
    symbols.append(sym)
result['changed_symbol_sizes']={k:[symbols[0][k],symbols[1][k]] for k in symbols[0].keys()&symbols[1].keys()
                                if symbols[0][k]['size']!=symbols[1][k]['size']}
print('changed symbol sizes',result['changed_symbol_sizes'])
(here/(a.prefix+'-diagnosis.json')).write_text(json.dumps(result,indent=2)+'\n')
