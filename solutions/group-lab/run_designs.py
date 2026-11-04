from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess,json
folder=Path(__file__).resolve().parent;root=folder.parents[1];out=folder/'designs';out.mkdir(exist_ok=True)
def job(item):
    m,g,mapping,q=item
    p=subprocess.run(['/tmp/ahc074-group-design',str(root/'tools/in/0024.txt'),str(m),str(g),str(mapping),'5000000',str(q)],capture_output=True,text=True,check=True,timeout=300)
    r=json.loads(p.stdout);r.update(M=m,G=g,mapping=mapping,initial_triples=q)
    (out/f'm{m}-g{g}-r{mapping}-q{q}.json').write_text(json.dumps(r,indent=2)+'\n')
    print(m,g,mapping,q,r.get('cost'),r.get('triples'),flush=True);return r
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(job,[(m,g,r,q) for m in (10,12,14,16,18,20) for g in (36,40,44,48) for r in (0,1) for q in (0,25)]))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
