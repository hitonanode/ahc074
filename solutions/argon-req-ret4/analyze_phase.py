from pathlib import Path
import subprocess
p=Path('solutions/argon-req-ret4')
def run(args,filename):
 with (p/filename).open('w') as f:subprocess.run(args,stdout=f,check=True)
run(['python3',str(p/'analyze.py'),'20261105-224849_esw-slim','20261105-224849_argon-req-ret4','20261105-224849_argon-req-ret4-joint','20261105-224849_argon-req-ret4-oracle','--json',str(p/'joint-oracle-200.json')],'joint-oracle-200.txt')
run(['python3',str(p/'metrics.py'),'20261105-224849_argon-req-ret4-oracle','--base','20261105-224849_esw-slim','--json',str(p/'oracle-200-metrics.json')],'oracle-200-metrics.txt')
for seed,r in [(64,738),(710,451),(36,465),(1883,350)]:
 for arm in ['esw-slim','argon-req-ret4']:
  run(['python3','scripts/observe.py','queries','20261105-222520_'+arm,str(seed),'--from',str(r-1),'--to',str(r+3),'--attr','role,col'],f'queries-{seed}-{arm}.txt')
print('Analysis complete.')
