"""Standard pahcer runner; locked/nice builds, optional per-arm compilers.
DCOMP_COMPILERS is JSON {solution_name: compiler}; DEVAL_NATIVE=1 applies -march=native.
No evaluation, timing, lock, recording, or solver policy is replaced.
"""
from pathlib import Path
import importlib.util,sys,os,json,hashlib,shutil
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('dcomp_pahcer',root/'scripts/pahcer_run.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
base_cmd=mod.COMPILE_CMD.copy()
compiler_map=json.loads(os.environ.get('DCOMP_COMPILERS','{}'))
original_prepare=mod.prepare_run
prefix=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10']
def prepare(solution,*args,**kwargs):
    compiler=compiler_map.get(Path(solution).name,os.environ.get('DEVAL_CXX','g++'))
    cmd=base_cmd.copy();cmd[0]=compiler
    if os.environ.get('DEVAL_NATIVE')=='1':cmd.insert(1,'-march=native')
    mod.COMPILE_CMD=prefix+cmd
    arm=original_prepare(solution,*args,**kwargs)
    arm['meta']['compiler']=mod.compiler_version(compiler)
    mod.save_meta(arm['run_dir'],arm['meta'])
    return arm
mod.prepare_run=prepare
original_compile=mod.compile_solution
def normalized(cmd):
    cmd=cmd[:cmd.index('-o')]
    if cmd[:3]==prefix[:3]:cmd=cmd[3:]
    if cmd[:3]==prefix[3:]:cmd=cmd[3:]
    return cmd
def compile_cached(cmd,run_dir,src_root):
    sha=hashlib.sha256(Path(cmd[-1]).read_bytes()).hexdigest()
    flags=normalized(cmd);version=mod.compiler_version(flags[0])
    if os.environ.get('DEVAL_BUILD_REUSE','1')!='0':
        for candidate in sorted(run_dir.parent.glob('*_'+src_root.name),reverse=True):
            if candidate==run_dir:continue
            try:
                m=json.loads((candidate/'meta.json').read_text())
                if m.get('status')!='ok' or m.get('compiler')!=version:continue
                if normalized(m['compile_command'])!=flags:continue
                if hashlib.sha256((candidate/'src/main.cpp').read_bytes()).hexdigest()!=sha:continue
                if not (candidate/'a.out').exists():continue
                shutil.copy2(candidate/'a.out',run_dir/'a.out')
                (run_dir/'compile.log').write_text(f'Reused exact source/compiler/flags build: {candidate.name}\nSHA256: {sha}\n')
                print('[dcomp] reused '+candidate.name,flush=True);return True
            except (OSError,KeyError,ValueError):pass
    return original_compile(cmd,run_dir,src_root)
mod.compile_solution=compile_cached
raise SystemExit(mod.main())
