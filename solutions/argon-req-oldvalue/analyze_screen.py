from pathlib import Path
import subprocess,re,statistics,json
names=['argon-req-filldp-positive','argon-req-oldvalue','argon-req-oldvalue-fix','argon-req-reserve','argon-req-oldvalue-reserve','argon-req-handlevalue']
runs=['20261106-003949_'+n for n in names]
subprocess.run(['python3','solutions/argon-req-oldvalue/analyze.py',*runs,'--json','solutions/argon-req-oldvalue/screen.json'],check=True)
root=Path('/home/sato/ahc074/runs');all_stats={}
for run in runs:
 r=root/run;files=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
 rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',p.read_text(),re.M)} for p in files]
 keys=[k for k in rows[0] if k.startswith(('old_value','value_filler','value_handle','reserve_')) or k in ['post_candidate_calls','interleave_trials']]
 stats={k:statistics.mean(row[k] for row in rows) for k in keys}
 all_stats[run]=stats;print(run,json.dumps(stats),flush=True)
Path('solutions/argon-req-oldvalue/screen-metrics.json').write_text(json.dumps(all_stats,indent=2)+'\n')
