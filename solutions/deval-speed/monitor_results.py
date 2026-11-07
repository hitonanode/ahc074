from pathlib import Path
import subprocess,sys,re,time,os,json
P=Path(__file__).resolve().parent
pending=['combined','funded2','coltable','colrun','ejectprefix','request-compact','request-threshold','gainprob']
while pending:
 for tag in pending[:]:
  f=P/(tag+'.log')
  if not f.exists() or 'ダッシュボードを更新しました' not in f.read_text():continue
  runs=re.findall(r'run-id: (\S+)',f.read_text())
  tasks=[(runs[0],r,tag+'.'+r.split('_',1)[1]+'.json') for r in runs[1:]]
  if 'argon-des-perf-latew105' in runs[0]:tasks += [(runs[1],r,tag+'.vbranch-vs-'+r.split('_',1)[1]+'.json') for r in runs[2:]]
  with (P/(tag+'-summary.log')).open('w') as out:
   for ref,run,target in tasks:
    subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'compare_runs.py'),ref,run,str(P/target)],stdout=out,check=True)
  if tag=='request-threshold':
   subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock',sys.executable,str(P/'analyze_quality.py'),runs[0],*runs[1:],'--seeds','0-500','--output',str(P/(tag+'-quality.json'))],check=True)
  print('analyzed',tag,flush=True);pending.remove(tag)
 if pending:time.sleep(10)
