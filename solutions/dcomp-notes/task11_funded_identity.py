from pathlib import Path
import re,runpy,sys
N=Path(__file__).resolve().parent;cc=sys.argv[1]
runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',(N/f't11-funded-{cc}.log').read_text(),re.M)
assert len(runs)==4
script=N/'task10_analyze.py'
sys.argv=[str(script),f't11-funded-{cc}-identity',runs[1],runs[2],'--seeds','0-500','--orders','1']
runpy.run_path(str(script),run_name='__main__')
