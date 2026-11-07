from pathlib import Path
import json,re,sys,subprocess
from compare_runs import main as compare_main
from analyze_quality import compare
P=Path(__file__).resolve().parent
for f in sorted(P.glob('*.log')):
 t=f.read_text(errors='replace')
 if 'ダッシュボードを更新しました' not in t or '比較が終わりました' not in t:continue
 runs=re.findall(r'^\[pahcer_run\] run-id: (\S+)',t,re.M)
 if len(runs)<2:continue
 tasks=[(runs[0],r,f.stem+'.'+r.split('_',1)[1]+'.json') for r in runs[1:]]
 if 'argon-des-perf-latew105' in runs[0]:tasks += [(runs[1],r,f.stem+'.vbranch-vs-'+r.split('_',1)[1]+'.json') for r in runs[2:]]
 if f.stem in ['resume-speed','fast2']:tasks += [(runs[1],r,f.stem+'.fast-vs-'+r.split('_',1)[1]+'.json') for r in runs[2:]]
 for a,b,target in tasks:
  if (P/target).exists():continue
  sys.argv=['compare_runs.py',a,b,str(P/target)];compare_main()
 if f.stem in ['request-threshold','requestfund','seven-wide']:
  out=[compare(runs[0],run,(0,500)) for run in runs[1:]]
  (P/(f.stem+'-quality.json')).write_text(json.dumps(out,indent=2)+'\n')
subprocess.run([sys.executable,str(P/'report_experiments.py')],check=True)
