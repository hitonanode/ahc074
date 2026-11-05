from pathlib import Path
import subprocess,json,math,statistics as st,re
p=Path('solutions/argon-req-ret4');root=Path('/home/sato/ahc074/runs');prefix='20261105-230220_'
names=['esw-slim','argon-req-ret4-late','argon-req-ret4-late-short','argon-req-ret4-joint']
with (p/'revisions-2000.txt').open('w') as f:
 subprocess.run(['python3',str(p/'analyze.py')]+[prefix+x for x in names]+['--json',str(p/'revisions-2000.json')],stdout=f,check=True)
def scores(name):
 return {x['seed']:x.get('order_scores',[x['score']]) for x in json.loads((root/name/'result.json').read_text())['cases']}
b=scores(prefix+'esw-slim');old=scores('20261105-222520_argon-req-ret4');prior_base=scores('20261105-222520_esw-slim')
assert b==prior_base
out={}
for name in names[1:]:
 r=root/(prefix+name);c=scores(prefix+name)
 d=[100*st.mean(math.log(y/x) for x,y in zip(old[k],c[k])) for k in sorted(b)]
 row={'versus_seed_log_pct':st.mean(d),'SE':st.stdev(d)/math.sqrt(len(d)),'WTL':[sum(x<0 for x in d),sum(x==0 for x in d),sum(x>0 for x in d)],'actual_moves_saved':sum(sum(b[k])-sum(c[k]) for k in b),'metrics':{}}
 for folder in [r]+sorted((r/'orders').glob('*')):
  for f in (folder/'err').glob('*.txt'):
   for k,v in re.findall(r'^(r1_late_\w+) = ([-+\d.eE]+)$',f.read_text(),re.M):row['metrics'][k]=row['metrics'].get(k,0)+float(v)
 out[name]=row
p.joinpath('revisions-detail.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
