"""Analyze a completed comparison using its exact run IDs (timestamps may straddle seconds)."""
from pathlib import Path
import argparse,re,runpy,sys
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('log');p.add_argument('--seeds',default='0-500');p.add_argument('--orders',type=int,default=1);a=p.parse_args()
runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)$',Path(a.log).read_text(),re.M);assert len(runs)>=2
script=Path(__file__).with_name('task10_analyze.py');sys.argv=[str(script),a.tag,*runs,'--seeds',a.seeds,'--orders',str(a.orders)]
runpy.run_path(str(script),run_name='__main__')
