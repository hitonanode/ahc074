from pathlib import Path
import json,subprocess,sys
from analyze_quality import compare
P=Path(__file__).resolve().parent
for tag in ['request-neighbors','combined','core-clang','colrun','coltable','ejectprefix']:
 f=P/(tag+'.log')
 if f.exists() and 'ダッシュボードを更新しました' in f.read_text():
  with (P/(tag+'-summary.log')).open('w') as out:subprocess.run([sys.executable,str(P/'analyze_log.py'),str(f)],stdout=out,check=True)
  print(tag,(P/(tag+'-summary.log')).read_text(),flush=True)
f=P/'request-neighbors.log'
if f.exists() and 'ダッシュボードを更新しました' in f.read_text():
 out=[]
 for name in ['reqmode2','reqinterior4','reqshort1','reqrefine1','reqwidth4']:
  r=compare('20261107-073324_deval-vbranch-o3','20261107-073324_deval-'+name,(0,500));out.append(r);print(name,r['results'],flush=True)
 (P/'request-neighbors-quality.json').write_text(json.dumps(out,indent=2)+'\n')
