from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,statistics,math
folder=Path(__file__).resolve().parent;out=folder/'designs';out.mkdir(exist_ok=True)
def task(seed):
 info=json.loads((folder/'templates'/f'{seed:04}.json').read_text())
 own=info['own'];base=f'/home/sato/ahc074/runs/20261103-171304_reset-majority/out/{seed:04}.txt';input=f'tools/in/{seed:04}.txt';prices=out/f'{seed:04}-prices.txt'
 r=subprocess.run(['/tmp/ahc074-mixed-front',input,base,'150',str(own[0]),str(own[1]),str(info['opaque']),str(prices)],text=True,capture_output=True,check=True)
 (out/f'{seed:04}-model.json').write_text(r.stdout);(out/f'{seed:04}-model.err').write_text(r.stderr)
 r=subprocess.run(['/tmp/ahc074-mixed-design',input,base,str(prices),'20000000'],text=True,capture_output=True,check=True)
 (out/f'{seed:04}-design.json').write_text(r.stdout);(out/f'{seed:04}-design.err').write_text(r.stderr)
 a,b=json.loads(r.stdout);row={'seed':seed,'difference':b['model']-a['model'],'rescued':b['rescued'],'template_rescues':info['rescued']};print(row,flush=True);return row
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(task,range(24,32)))
x=[r['difference'] for r in rows];result={'cases':len(x),'difference':statistics.mean(x),'se':statistics.stdev(x)/math.sqrt(len(x)),'mean_rescued':statistics.mean(r['rescued'] for r in rows),'rows':rows}
(out/'summary.json').write_text(json.dumps(result,indent=2));print(result)
