from pathlib import Path
import sys,re
from compare_runs import main
P=Path(__file__).resolve().parent
for tag in ['fast2','fast2-clang','climbcache','climbcache-clang']:
 f=P/(tag+'.log')
 if not f.exists():continue
 txt=f.read_text()
 if 'ダッシュボードを更新しました' not in txt:continue
 runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)',txt,re.M)
 for candidate in runs[1:]:
  dst=P/(tag+'.'+candidate.split('_',1)[1]+'.json')
  sys.argv=['compare_runs',runs[0],candidate,str(dst)];main()
