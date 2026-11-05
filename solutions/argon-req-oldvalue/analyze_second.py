from pathlib import Path
import subprocess,re,statistics as st,json
names=['argon-req-filldp-positive','argon-req-completevalue','argon-req-seed-direct','argon-req-seed-eject','argon-req-jointk2','argon-req-jointk4'];runs=['20261106-013252_'+s for s in names]
subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',*runs,'--json','solutions/argon-req-oldvalue/second.json'],check=True)
root=Path('/home/sato/ahc074/runs');allstats={}
for run in runs:
 p=root/run;fs=list((p/'err').glob('*.txt'))+list((p/'orders').glob('*/err/*.txt'))
 rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',f.read_text(),re.M)} for f in fs]
 vals={k:st.mean(r.get(k,0) for r in rows) for k in rows[0] if k.startswith(('complete_value','late_seed','joint_extra','value_filler'))}
 print(run,vals);allstats[run]=vals
Path('solutions/argon-req-oldvalue/second-metrics.json').write_text(json.dumps(allstats,indent=2)+'\n')
