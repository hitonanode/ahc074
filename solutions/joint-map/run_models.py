import subprocess,json,statistics,math,concurrent.futures
from pathlib import Path
out=Path(__file__).parent/'models';out.mkdir(exist_ok=True)
def task(seed):
 args=['/tmp/ahc074-joint-greedy',f'tools/in/{seed:04}.txt',f'/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{seed:04}.txt','2000','8','2.0','10000','1']
 p=subprocess.run(args,capture_output=True,text=True,check=True)
 (out/f'{seed:04}.json').write_text(p.stdout);(out/f'{seed:04}.err').write_text(p.stderr)
 x=json.loads(p.stdout);assert all(not a['wrong'] for a in x);print(seed,x[-1],flush=True);return x[-1]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(task,range(24,40)))
x=[a['difference'] for a in r];s={'n':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'win_tie_loss':[sum(a<0 for a in x),sum(a==0 for a in x),sum(a>0 for a in x)],'edge_changes':statistics.mean(a['edge_changes'] for a in r),'seconds':statistics.mean(a['seconds'] for a in r)}
(out/'summary.json').write_text(json.dumps(s));print(s)
