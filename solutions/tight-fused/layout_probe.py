from pathlib import Path
import subprocess,os,re,json,math,statistics,fcntl,time
p=Path(__file__).resolve().parent;out=p/'layout';out.mkdir(exist_ok=True)
root=Path('/home/sato/ahc074');bins=[root/'runs'/('20261104-071059_'+s)/'a.out'for s in ['tight-thirty-eight','tight-fused']]
env=os.environ.copy();env.update(MAP_ITERS='100000',GOPT_STEPS='25000',ANNEAL_ITERS='1024',CLIMB_ITERS='-1')
lock=open(root/'runs/.lock','rb');rows=[]
for seed in range(1256,1288):
 fcntl.flock(lock,fcntl.LOCK_SH)
 # Only the public header and 256 patterns are supplied, followed by the termination code.
 with (root/'tools/in'/f'{seed:04}.txt').open()as f:data=''.join(next(f)for _ in range(257))+'-1\n'
 row=[[],[]];prints=[None,None]
 for step in range(4):
  mode=(seed+step)%2;r=subprocess.run([str(bins[mode])],input=data,text=True,capture_output=True,env=env,check=True,timeout=30)
  values={k:float(v)for k,v in re.findall(r'^([a-z_]+) = ([\d.eE+-]+)$',r.stderr,re.M)}
  row[mode].append(values);prints[mode]=r.stdout
 fcntl.flock(lock,fcntl.LOCK_UN)
 assert prints[0]==prints[1],seed
 (out/f'{seed:04}.json').write_text(json.dumps(row));rows.append(row);print(seed,[statistics.mean(v['map_end_sec']for v in r)for r in row],flush=True)
v=[100*math.log(statistics.mean(x['map_end_sec']for x in r[1])/statistics.mean(x['map_end_sec']for x in r[0]))for r in rows]
summary={'cases':len(rows),'log_time_ratio_pct':statistics.mean(v),'se_pct':statistics.stdev(v)/math.sqrt(len(v)),'seconds':[statistics.mean(x['map_end_sec']for r in rows for x in r[m])for m in range(2)]}
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
