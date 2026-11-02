#!/usr/bin/env python3
"""Assignment-only exploration curve; deliberately does not evaluate contest scores."""
import csv,hashlib,json,math,os,pathlib,re,statistics,subprocess,time
here=pathlib.Path(__file__).resolve().parent
root=here.parents[1]
inputs=pathlib.Path(os.environ.get('ASTRA_INPUT_DIR', str(root/'solutions/astra-lab/cases')))
out=here/'curve'
out.mkdir(exist_ok=True)
configs=[('base',800000,200000),('joint',10000,2500),('joint',50000,12500),('joint',100000,25000)]
rows=[]
for seed in range(8):
 data=b''.join((inputs/f'{seed:04}.txt').read_bytes().splitlines(keepends=True)[:257])
 for variant,m,g in configs:
  label=f'{variant}-{m}'
  env=dict(os.environ,MAP_ITERS=str(m),GOPT_STEPS=str(g))
  t=time.perf_counter()
  result=subprocess.run([str(here/f'probe-{variant}')],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=180)
  text=result.stderr.decode()
  (out/f'{label}-{seed:04}.log').write_text(text)
  row=dict(seed=seed,variant=label,map_iters=m,gopt_steps=g,wall_seconds=time.perf_counter()-t,returncode=result.returncode)
  for key,value in re.findall(r'^([A-Za-z_][A-Za-z_0-9]*) = ([0-9.eE+-]+)$',text,re.M):row[key]=float(value)
  rows.append(row)
  print({k:row.get(k) for k in ['seed','variant','returncode','probe_gobj','probe_map_sec','joint_matched','joint_global_repairs']},flush=True)
  keys=sorted({k for x in rows for k in x})
  with (here/'exploration-curve.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
  (here/'exploration-curve.json').write_text(json.dumps({'measurement':'assignment objective only, no contest scores','input_generator':'Python MT19937 seeds74000000..74000007','joint_source_sha256':hashlib.sha256((here/'main.cpp').read_bytes()).hexdigest(),'baseline_source_sha256':hashlib.sha256((root/'solutions/astra-search4/main.cpp').read_bytes()).hexdigest(),'rows':rows},ensure_ascii=False,indent=2)+'\n')
