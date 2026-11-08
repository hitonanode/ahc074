"""Call scripts/pahcer_run.py, adding flock to its otherwise-unlocked compiler.

The runner's normal evaluation lock and all recording are left intact.
"""
from pathlib import Path
import importlib.util
import sys
import os
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('deval_pahcer_run',root/'scripts/pahcer_run.py')
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
# The standard runner validates absolute --design-from paths but records only
# their basename; arm_env then wrongly rebuilds runs/<basename>/design. Preserve
# the absolute reference for our captured artifacts outside runs/. Ordinary
# saved-design runs retain the standard behavior. No solver policy is changed.
original_design_source=mod.design_source
def artifact_design_source(arg):
    source_id,design_dir=original_design_source(arg)
    parent=design_dir.resolve().parent
    try:
        local=parent.relative_to(root/'solutions')
    except ValueError:
        return source_id,design_dir
    if local.parts and local.parts[0].startswith('dcomp-'):
        return str(parent),design_dir
    return source_id,design_dir
mod.design_source=artifact_design_source
compiler=os.environ.get('DEVAL_CXX','g++')
mod.COMPILE_CMD[0]=compiler
if os.environ.get('DEVAL_NATIVE')=='1':mod.COMPILE_CMD.insert(1,'-march=native')
compiler_version=mod.compiler_version
mod.compiler_version=lambda _:compiler_version(compiler)
mod.COMPILE_CMD=['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10']+mod.COMPILE_CMD
# Reuse only a completed build of this exact one-file source and compiler flags.
# The standard runner still snapshots sources, executes, locks, and records every case.
if os.environ.get('DEVAL_BUILD_REUSE','1') != '0':
    import hashlib,json,shutil
    original_compile=mod.compile_solution
    def cached_compile(cmd,run_dir,src_root):
        source=Path(cmd[-1])
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        prefix=cmd[:cmd.index('-o')]
        def normalized(c):
            c=c[:c.index('-o')]
            if c[:3]==['flock','-x','/home/sato/ahc074/runs/.lock']:c=c[3:]
            if c[:3]==['nice','-n','10']:c=c[3:]
            return c
        name=src_root.name
        version=mod.compiler_version(compiler)
        for candidate in sorted(run_dir.parent.glob('*_'+name),reverse=True):
            if candidate==run_dir:continue
            try:
                m=json.loads((candidate/'meta.json').read_text())
                if m.get('status')!='ok' or m.get('compiler')!=version:continue
                if normalized(m['compile_command'])!=normalized(cmd):continue
                if hashlib.sha256((candidate/'src/main.cpp').read_bytes()).hexdigest()!=digest:continue
                if not (candidate/'a.out').exists():continue
                shutil.copy2(candidate/'a.out',run_dir/'a.out')
                (run_dir/'compile.log').write_text('Reused exact source / compiler / flags build: '+str(candidate)+'\nSHA256 source: '+digest+'\n')
                print('[deval] reused build: '+candidate.name,flush=True)
                return True
            except (OSError,ValueError,KeyError):continue
        return original_compile(cmd,run_dir,src_root)
    mod.compile_solution=cached_compile
raise SystemExit(mod.main())
