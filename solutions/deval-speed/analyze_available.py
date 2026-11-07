from pathlib import Path
import subprocess,sys,json
from analyze_quality import compare
HERE=Path(__file__).resolve().parent
for tag in ['geometry','negative','radixscan','hungarian-vec','perfint','smallfill','colcache']:
    f=HERE/(tag+'.log');summary=HERE/(tag+'-summary.log')
    if f.exists() and 'ダッシュボードを更新しました' in f.read_text() and not summary.exists():
        with summary.open('w') as out:subprocess.run([sys.executable,str(HERE/'analyze_log.py'),str(f)],stdout=out,check=True)
    if summary.exists():print(tag+'\n'+summary.read_text(),flush=True)
manifest=HERE/'experiments.jsonl'
if manifest.exists():
    out=[]
    for line in manifest.read_text().splitlines():
        r=json.loads(line)
        a=compare('20261107-062543_deval-vbranch-o3',r['replay'],(0,500));a['experiment']=r;out.append(a)
        print(r['tag'],a['results'],flush=True)
    (HERE/'quality.json').write_text(json.dumps(out,indent=2)+'\n')
refs='20261107-072037_deval-vbranch-o3'
request=[]
for name in ['reqpost5','reqround3','reqvalue','reqhidden0','reqshort0','reqanchors1']:
    r=compare(refs,'20261107-072037_deval-'+name,(0,500));request.append(r)
    print(name,r['results'],flush=True)
(HERE/'request-settings-quality.json').write_text(json.dumps(request,indent=2)+'\n')
