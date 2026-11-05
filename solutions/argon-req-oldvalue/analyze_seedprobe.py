from pathlib import Path
import re,json,statistics as st
root=Path('/home/sato/ahc074/runs')
run='20261106-011806_argon-req-seedprobe'
r=root/run
fs=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
rows=[dict((k,float(v)) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)) for f in fs]
values={k:st.mean(row[k] for row in rows) for k in rows[0] if k.startswith(('seed_probe_','late_seed_'))}
for b in range(12):
 for g in [0,2,3,4,6]:
  d={k:values[f'seed_probe_{b}_{g}_{k}'] for k in ['trials','better','gain','moves','sec']}
  if d['trials']:print('novel',b//6,'best',b//3%2,'stage',b%3,'gate',g,d)
print('TOTAL')
for g in range(7):
 for pick in ['all','novel','notnovel','stage1','stage2','novelstage1','novelstage2']:
  bs=[b for b in range(12) if (('notnovel' not in pick or b<6) and ('novel' not in pick or 'notnovel' in pick or b>=6) and ('stage1' not in pick or b%3==1) and ('stage2' not in pick or b%3==2))]
  print(g,pick,{k:sum(values[f'seed_probe_{b}_{g}_{k}'] for b in bs) for k in ['trials','better','gain','moves','sec']})
outs=list((r/'out').glob('*.txt'))+list((r/'orders').glob('*/out/*.txt'))
base=root/'20261106-011806_argon-req-filldp-positive'
print('stdout identical',sum(p.read_bytes()==(base/p.relative_to(r)).read_bytes() for p in outs),'/',len(outs))
Path('solutions/argon-req-oldvalue/seedprobe-metrics.json').write_text(json.dumps(values,indent=2)+'\n')
