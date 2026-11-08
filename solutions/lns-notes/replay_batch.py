from pathlib import Path
import subprocess,sys,json,argparse,re,time
here=Path(__file__).resolve().parent;root=here.parents[1];R=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('runs',nargs='+');p.add_argument('--seeds',default='0-500');p.add_argument('--orders',type=int,default=8);a=p.parse_args()
rows=[]
for source in a.runs:
 d=Path(source) if Path(source).is_dir() else R/source
 assert (d/'meta.json').exists(),d
 m=json.loads((d/'meta.json').read_text())
 while m.get('status') not in ['ok','artifact']:
  assert m.get('status') not in ['compile_error','error','failed'],(d,m.get('status'))
  time.sleep(10);m=json.loads((d/'meta.json').read_text())
 log=here/(a.tag+'-'+d.name+'.log')
 cmd=[sys.executable,str(here/'run.py'),'solutions/deval-helper-wide','--design-from',str(d),'--orders',str(a.orders),'--seeds',a.seeds,'-c','Task7 '+a.tag+': fixed helper-wide request policy; source '+str(d)]
 with log.open('w') as f:subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 ids=re.findall(r'run-id: (\S+)',log.read_text());assert len(ids)==1,ids
 replay=ids[0];assert json.loads((R/replay/'meta.json').read_text())['status']=='ok'
 cases=json.loads((R/replay/'result.json').read_text())['cases']
 assert cases and all(min(c.get('order_scores',[c['score']]))>0 for c in cases),('WA in replay',replay)
 rows.append({'source':str(d),'replay':replay,'seeds':a.seeds,'orders':a.orders});(here/(a.tag+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
 print(d.name,replay,flush=True)
