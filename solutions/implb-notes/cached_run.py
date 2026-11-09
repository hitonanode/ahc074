"""Standard pahcer runner; reuse only an exactly matching GCC smoke build.
Case execution, comparison, locking, records and extensions are pahcer_run.py unchanged.
The original compile command and build_reused_from are both saved in meta.json.
"""
from pathlib import Path
import importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('b_cached_pahcer',root/'scripts/pahcer_run.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
mod.COMPILE_CMD=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','g++','-std=c++23','-O2','-DCLOCK_SCALE=1.1','-DLOCAL_BENCH']
original_compile=mod.compile_solution
original_prepare=mod.prepare_run
arms={}
def prepare(*args,**kwargs):
 arm=original_prepare(*args,**kwargs);arm['meta']['compiler']=mod.compiler_version('g++')
 arms[str(arm['run_dir'])]=arm
 mod.save_meta(arm['run_dir'],arm['meta'])
 return arm
mod.prepare_run=prepare
cache_prefix=os.environ.get('D30B_BUILD_CACHE','20261109-115349')
def normalized(cmd):
 cmd=list(cmd);i=cmd.index('-o');cmd[i+1]='<binary>';cmd[-1]='<source>'
 return cmd
def compile_cached(cmd,run_dir,src_root):
 run_dir=Path(run_dir);meta=arms[str(run_dir)]['meta']
 name=run_dir.name.split('_',1)[1]
 old=Path('/home/sato/ahc074/runs')/(cache_prefix+'_'+name)
 if (old/'a.out').exists() and (old/'meta.json').exists():
  om=json.loads((old/'meta.json').read_text())
  same_flags=normalized(cmd)==normalized(om['compile_command'])
  same_source=(old/'src/main.cpp').read_bytes()==(run_dir/'src/main.cpp').read_bytes()
  if same_flags and same_source and om.get('compiler')==meta.get('compiler'):
   subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10','cp',str(old/'a.out'),str(run_dir/'a.out')],check=True)
   meta['build_reused_from']=old.name;meta['build_reuse_verified']=['source_bytes','compile_flags','compiler_version'];mod.save_meta(run_dir,meta)
   mod.log(f'exact build reuse: {old.name} -> {run_dir.name}')
   return True
 return original_compile(cmd,run_dir,src_root)
mod.compile_solution=compile_cached
raise SystemExit(mod.main())
