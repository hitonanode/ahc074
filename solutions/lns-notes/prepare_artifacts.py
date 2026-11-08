from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--source',required=True);a=p.parse_args()
root=Path(a.directory).resolve();run=Path('/home/sato/ahc074/runs')/a.source
meta=json.loads((run/'meta.json').read_text());assert meta['status']=='ok'
source_sha=hashlib.sha256((run/'src/main.cpp').read_bytes()).hexdigest()
for d in sorted(root.glob('candidate-*')):
 n=len(list((d/'design').glob('*.txt')))
 (d/'meta.json').write_text(json.dumps({'status':'artifact','source_run':a.source,'source_sha256':source_sha,'candidate_id':int(d.name.split('-')[1]),'saved_cases':n,'request_policy':'deval-helper-wide','note':'DesignState captured during a standard pahcer_run.py design run; not an independent scored run.'},indent=2)+'\n')
 print(d,n)
