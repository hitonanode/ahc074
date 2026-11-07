#!/usr/bin/env python3
"""Recorded, fixed-work comparisons on identical immutable paper designs.
Not the official Rust tester or the repository's pahcer evaluation history.
"""
import argparse,concurrent.futures,csv,hashlib,json,math,os,statistics,subprocess,time
from pathlib import Path
PROFILES={
 'base':{},
 'mdp':{'COLUMN_CONTROL':'.25'},
 'prior_best':{'COLUMN_CONTROL':'.25','OLD_HELPER':'1','POST_CANDIDATES':'4'},
 'families3':{'DP_RANKS':'3','DP_CONTEXTS':'2','DP_FAMILIES':'1'},
 'mdp_family':{'COLUMN_CONTROL':'.25','DP_RANKS':'3','DP_CONTEXTS':'2','DP_FAMILIES':'1'},
 'combined':{'COLUMN_CONTROL':'.25','DP_RANKS':'7','DP_CONTEXTS':'2','DP_FAMILIES':'1','POST_CANDIDATES':'4','EJECT_EACH':'1','WARM_HELPERS':'1'},
}
ZERO_KEYS='WARM_HELPERS ANCHOR_ALL HELPER_RELAX HELPER_ORDER SUFFIX_CUT HEAD_POTENTIAL EJECT_ALL_TIMES DELETE_ALL_PAIRS EJECT_EACH INIT_MODE NO_FILLER_PLANS COLUMN_CONTROL DP_RANKS DP_FAMILIES DP_TIE_MODE DP_CACHE OLD_HELPER'.split()
FIXED=dict(FIXED_WORK='1',NO_FALLBACK='1',MAP_ITERS='262144',GOPT_STEPS='65536',ANNEAL_ITERS='12582912',CLIMB_ITERS='32768',POST_CANDIDATES='2',DP_CONTEXTS='1')
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic(path,value):
 t=path.with_suffix(path.suffix+'.tmp');t.write_text(json.dumps(value,indent=2)+'\n');t.replace(path)
def compare(rows,name,base='base'):
 ids=sorted({r['case']for r in rows});scores={(r['case'],r['name']):r['moves']for r in rows}
 x=[scores[i,name]for i in ids];y=[scores[i,base]for i in ids];z=[100*math.log(a/b)for a,b in zip(x,y)];n=len(z)
 return dict(n=n,total=sum(x),baseline_total=sum(y),saved_moves=sum(y)-sum(x),total_reduction_percent=100*(sum(y)-sum(x))/sum(y),mean_log_ratio_percent=statistics.mean(z),se_percent=statistics.stdev(z)/math.sqrt(n)if n>1 else None,wins=sum(a<b for a,b in zip(x,y)),ties=sum(a==b for a,b in zip(x,y)),losses=sum(a>b for a,b in zip(x,y)))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--solver',type=Path,required=True);p.add_argument('--checker',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=128);p.add_argument('--jobs',type=int,default=2);p.add_argument('--timeout',type=float,default=300)
 a=p.parse_args();a.solver=a.solver.resolve();a.checker=a.checker.resolve();a.out=a.out.resolve()
 if a.out.exists()and any(a.out.iterdir()):p.error('--out must be empty or absent')
 if a.count<1 or a.jobs<1:p.error('count and jobs must be positive')
 for name in ['inputs','designs','runs']:(a.out/name).mkdir(parents=True,exist_ok=True)
 expected_file=Path(__file__).resolve().parent/'results/input-hashes.json';expected=json.loads(expected_file.read_text())if expected_file.exists()else{}
 metadata=dict(profiles=PROFILES,fixed=FIXED,solver_sha256=sha(a.solver.read_bytes()),checker_sha256=sha(a.checker.read_bytes()),case_start=a.start,case_count=a.count,generator='C++ mt19937_64, seed=880074000+case; not official ChaCha20 seed IDs',official_rust_tester=False)
 atomic(a.out/'metadata.json',metadata)
 def case(i):
  inp=a.inputs/f'{i:04}.txt' if a.inputs else a.out/'inputs'/f'{i:04}.txt'
  if not a.inputs:subprocess.run([str(a.checker),'gen',str(880074000+i),str(inp)],check=True)
  ih=sha(inp.read_bytes())
  if str(i)in expected and expected[str(i)]!=ih:raise ValueError(f'input {i} differs from the recorded corpus; use archived inputs or the recorded generator environment')
  design=a.out/'designs'/f'{i:04}.txt';names=list(PROFILES)[1:];names=names[i%len(names):]+names[:i%len(names)];names=['base']+names;rows=[];papers=None
  for name in names:
   env=os.environ.copy()
   for key in ['LOAD_DESIGN','SAVE_DESIGN','DESIGN_ONLY','SIM_SEQS','WARM_LENGTH']:env.pop(key,None)
   env.update({k:'0'for k in ZERO_KEYS});env.update(FIXED);env.update(PROFILES[name]);env['SAVE_DESIGN'if name=='base'else'LOAD_DESIGN']=str(design)
   out=a.out/'runs'/f'{name}-{i:04}.out';err=out.with_suffix('.err');start=time.perf_counter()
   with inp.open('rb')as fi,out.open('wb')as fo,err.open('wb')as fe:
    completed=subprocess.run([str(a.solver)],stdin=fi,stdout=fo,stderr=fe,env=env,timeout=a.timeout)
   if completed.returncode:raise RuntimeError(f'{name} case {i}: exit {completed.returncode}; see {err}')
   check=json.loads(subprocess.check_output([str(a.checker),str(inp),str(out)],text=True))
   if not check.get('valid')or check['errors']:raise RuntimeError((i,name,check))
   data=out.read_bytes();pp=data.splitlines()[:192]
   if papers is None:papers=pp
   elif pp!=papers:raise AssertionError('paper designs differ')
   stats=dict(l.split(' = ',1)for l in err.read_text().splitlines()if' = 'in l)
   if stats.get('fast_requests')!='0':raise AssertionError('request degradation detected')
   row=dict(case=i,name=name,input_sha256=ih,output_sha256=sha(data),wall_sec=time.perf_counter()-start,stats=stats,**check);rows.append(row);atomic(out.with_suffix('.json'),row)
   print(i,name,check['moves'],flush=True)
  return rows
 rows=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs)as ex:
  for batch in ex.map(case,range(a.start,a.start+a.count)):
   rows+=batch;atomic(a.out/'rows.json',rows)
 summary={n:compare(rows,n)for n in PROFILES if n!='base'};summary['combined_vs_prior_best']=compare(rows,'combined','prior_best');summary['mdp_family_vs_mdp']=compare(rows,'mdp_family','mdp');atomic(a.out/'summary.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
