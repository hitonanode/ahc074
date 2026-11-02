from pathlib import Path
import subprocess,os,sys,json,hashlib
r=Path(__file__).resolve().parent;(r/'work').mkdir(exist_ok=True);env=os.environ.copy();env['TMPDIR']=str(r/'work');env['PYTHONDONTWRITEBYTECODE']='1'
subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(r.parent/'as6-cap38/main.cpp'),'-o',str(r/'work/base')],env=env,check=True)
for name,src,old in [('main','main.cpp','final-main'),('cand2','cand2/main.cpp','final-cand2')]:
 oldsrc='combo.cpp' if name=='main' else 'repair.cpp'
 subprocess.run(['g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(r/oldsrc),'-o',str(r/'work'/old)],env=env,check=True)
 for cc,suf in [('g++',''),('clang++','-clang')]:
  subprocess.run([cc,'-std=c++23','-O2','-DCLOCK_SCALE=1.1',str(r/src),'-o',str(r/'work'/('delivery-'+name+suf))],env=env,check=True)
 print('compiled',name,flush=True)
 for label,bins,seeds,fixed in [
  (f'setup-{name}-control',[f'before={r}/work/{old}',f'after={r}/work/delivery-{name}'],'24:32','200000,50000,10000000,10000'),
  (f'delivery-{name}-64',[f'base={r}/work/base',f'{name}={r}/work/delivery-{name}'],'24:88',''),
  (f'delivery-{name}-clang-smoke',[f'gcc={r}/work/delivery-{name}',f'clang={r}/work/delivery-{name}-clang'],'88:92','200000,50000,10000000,10000')]:
  if env.get('RESUME_DELIVERY')=='1' and (r/'results'/f'{label}.json').exists():continue
  cmd=[sys.executable,str(r/'bench.py'),'--label',label,'--bins',*bins,'--seeds',seeds,'--threads','8' if not fixed else '4']
  if fixed:cmd+=['--fixed',fixed]
  with (r/'work'/f'{label}.log').open('w') as f:subprocess.run(cmd,stdout=f,env=env,check=True)
  print('tested',label,flush=True)
# Exact structural comparison: same fixed design/search, cap starts at top.
checks=[]
for name in ['main','cand2']:
 x=json.load(open(r/'results'/f'setup-{name}-control.json'))
 rows={(a['seed'],a['name']):a['stats'] for a in x['cases']}
 for seed in range(24,32):
  before,after=rows[seed,'before'],rows[seed,'after']
  assert after['Score']==before['Score']-1,(name,seed,before['Score'],after['Score'])
  assert after['model_cost']==before['model_cost']
  checks.append({'name':name,'seed':seed,'before':before['Score'],'after':after['Score']})
sys.dont_write_bytecode=True;sys.path.insert(0,str(r.parent.parent/'scripts'));import replay
verified=[]
for name in ['main','cand2']:
 for suffix in ['64','clang-smoke']:
  label=f'delivery-{name}-{suffix}';x=json.load(open(r/'results'/f'{label}.json'))
  for row in x['cases']:
   seed,variant=row['seed'],row['name'];op=r/'work'/label/f'{variant}-{seed:04d}.out'
   inp=replay.parse_input(Path(f'/home/sato/ahc074/tools/in/{seed:04d}.txt').read_text());out=replay.parse_output(inp,op.read_text())
   assert out.error is None and len(out.queries)==1024 and row['stats']['Score']==out.moves and row['stats']['self_wrong']==0
   verified.append({'run':label,'seed':seed,'variant':variant,'T':out.moves,'E':0,'sha256':hashlib.sha256(op.read_bytes()).hexdigest()})
(r/'results/delivery-correctness.json').write_text(json.dumps({'setup_control':checks,'verified_cases':len(verified),'cases':verified},indent=2)+'\n')
manifest={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in ['main.cpp','cand2/main.cpp']};manifest['base']=hashlib.sha256((r.parent/'as6-cap38/main.cpp').read_bytes()).hexdigest()
(r/'results/source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('All setup savings = 1; official E = 0.',flush=True)
