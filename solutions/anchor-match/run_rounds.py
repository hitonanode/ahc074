from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
p=Path(__file__).resolve().parent;out=p/'rounds';out.mkdir(exist_ok=True)
def run(seed):
 r=subprocess.run(['/tmp/ahc074-anchor-rounds',f'/home/sato/ahc074/tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt','16','8'],text=True,capture_output=True,check=True)
 (out/f'{seed:04}.json').write_text(r.stdout);(out/f'{seed:04}.err').write_text(r.stderr)
 rows=json.loads(r.stdout);print(seed,[(x['rounds'],x['difference'],x['match_seconds'])for x in rows],flush=True);return rows
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,range(24,56)))
summary={}
for count in (1,2,4,8):
 x=[next(r for r in row if r['rounds']==count)for row in rows];d=[r['difference']for r in x]
 summary[count]=dict(mean=statistics.mean(d),se=statistics.stdev(d)/math.sqrt(len(d)),wins=sum(v<0 for v in d),ties=sum(v==0 for v in d),losses=sum(v>0 for v in d),model=statistics.mean(r['decrease']for r in x),seconds=statistics.mean(r['match_seconds']for r in x))
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
