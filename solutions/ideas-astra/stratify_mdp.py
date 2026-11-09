from pathlib import Path
import json,re,statistics,math,argparse
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--output',required=True);a=p.parse_args()
root=Path('/home/sato/ahc074/runs');rx=re.compile(r'^([A-Za-z][A-Za-z0-9_]*) = ([-+0-9.eE]+)$',re.M)
def logs(run):return {int(p.stem):{k:float(v) for k,v in rx.findall(p.read_text())} for p in (root/run/'err').glob('*.txt')}
b=logs(a.base);c=logs(a.candidate)
result={}
for group in ['all','partial','full']:
 ids=[i for i in b if i in c and (group=='all' or (b[i]['colmdp_columns']<25)==(group=='partial'))]
 ds=[1000*(c[i]['req_sec']-b[i]['req_sec']) for i in ids]
 result[group]={'n':len(ids),'req_ms':statistics.mean(ds),'se_ms':statistics.stdev(ds)/math.sqrt(len(ds)) if len(ds)>1 else 0,'seeds':ids}
print(json.dumps(result,ensure_ascii=False,indent=2));Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
