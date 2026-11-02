"""Local research runner, eight solvers maximum (six for tester mode).
No pahcer metadata or files outside this directory are written.
"""
import argparse, concurrent.futures as cf, hashlib, json, math, os, pathlib, re, statistics, subprocess, time
D=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--label',required=True);p.add_argument('--seeds',default='24-88');p.add_argument('--extra',action='append',default=[]);p.add_argument('--sim',type=int,default=0);p.add_argument('--tester',action='store_true');p.add_argument('--workers',type=int,default=8);args=p.parse_args()
lo,hi=map(int,args.seeds.split('-'));binary=D/args.binary
extra=dict(x.split('=',1) for x in args.extra)
fixed={} if args.tester else dict(MAP_ITERS='400000',GOPT_STEPS='100000',ANNEAL_ITERS='20000000',CLIMB_ITERS='60000',MODEL_ONLY='0' if args.sim else '1',DUMP_DESIGN='0',SIM_SEQS=str(args.sim))
env=os.environ|fixed|extra
outdir=D/'results'/args.label;outdir.mkdir(parents=True,exist_ok=True)
meta={'binary':args.binary,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'fixed':fixed,'extra':extra,'seeds':[lo,hi],'sim_sequences':args.sim,'tester':args.tester}
(outdir/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
def job(seed):
 dst=outdir/f'{seed:04d}.json'
 if dst.exists():return json.loads(dst.read_text())
 t=time.monotonic();cmd=[str(binary)]
 if args.tester:cmd=['/home/sato/ahc074/tools/target/release/tester']+cmd
 with open(f'/home/sato/ahc074/tools/in/{seed:04d}.txt','rb') as inp:r=subprocess.run(cmd,stdin=inp,capture_output=True,env=env,timeout=900)
 log=r.stderr.decode(errors='replace')
 metrics={m[0]:float(m[1]) for m in re.findall(r'(?m)^(\w+) = ([-+0-9.eE]+)$',log)}
 record={'seed':seed,'returncode':r.returncode,'metrics':metrics,'wall_sec':time.monotonic()-t}
 if r.returncode or (not args.tester and 'model_cost' not in metrics):record['error']=log[-3000:]
 dst.write_text(json.dumps(record,separators=(',',':'))+'\n');(outdir/f'{seed:04d}.err').write_text(log)
 if args.tester:(outdir/f'{seed:04d}.out').write_bytes(r.stdout)
 print('finished',args.label,seed,record['metrics'].get('model_cost'),record['metrics'].get('sim_moves'),flush=True)
 return record
with cf.ThreadPoolExecutor(max_workers=min(args.workers,6 if args.tester else 8)) as pool:rows=list(pool.map(job,range(lo,hi)))
keys=set.intersection(*(set(x['metrics']) for x in rows))
summary={k:{'mean':statistics.mean(x['metrics'][k] for x in rows),'max':max(x['metrics'][k] for x in rows)} for k in sorted(keys)}
summary['failed']=sum(bool(x.get('error')) for x in rows);summary['n']=len(rows)
(outdir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
