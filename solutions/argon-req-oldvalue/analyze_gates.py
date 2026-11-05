from pathlib import Path
import re,json,statistics,subprocess
run='20261106-005721_argon-req-oldvalue-gateprobe';root=Path('/home/sato/ahc074/runs');r=root/run
files=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)} for f in files]
mean=lambda key:statistics.mean(x.get(key,0) for x in rows)
out={k:mean(k) for k in rows[0] if k.startswith('old_') and not k[-1].isdigit()}
Path('solutions/argon-req-oldvalue/gates-metrics.json').write_text(json.dumps(out,indent=2)+'\n')
for mode in range(5):
 print('mode',mode,'valid/raw_existing/same/better/gain/moves',[mean(f'old_probe_{mode}_{k}') for k in ['valid','raw_existing','same','better','gain','moves']])
 for g,lim in enumerate([0,.25,.5,1,1.5,2,3]):
  print(' gap',lim,'calls/wins/value/moves',[mean(f'old_gate_{mode}_{g}_{k}') for k in ['calls','better','gain','moves']])
print('residual',{k:v for k,v in out.items() if k.startswith('old_probe_residual')})
outs=list((r/'out').glob('*.txt'))+list((r/'orders').glob('*/out/*.txt'));b=root/'20261106-005721_argon-req-filldp-positive'
print('stdout_matches',sum(p.read_bytes()==(b/p.relative_to(r)).read_bytes() for p in outs),'/',len(outs))
subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py','20261106-005721_argon-req-filldp-positive','20261106-005721_argon-req-prevalue','--json','solutions/argon-req-oldvalue/prevalue.json'],check=True)
