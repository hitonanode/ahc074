#!/usr/bin/env python3
"""Paired online evaluation of public-input-only frozen designs via pahcer_run.

Design construction time is deliberately NOT included in online execution_time.
See preparation/search logs for total experimental compute. This is not a 2s claim.
"""
import argparse, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import pahcer_run
ARMS=[]
DESIGNS=None
SOURCE_MAP={}

def publish(path,data):
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.')
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def compare_case(seed,order,binaries,run_dirs,in_dir,tester):
    records=[{} for _ in binaries]
    for i in order:
        source_seed=SOURCE_MAP.get(seed,seed)
        path=DESIGNS/str(source_seed)/ARMS[i]
        env=os.environ.copy();env.update(JOINT_STAGE='play',JOINT_INPUT=str(path),JOINT_FORCE_BFS='0' if ARMS[i]=='legacy.design' else '1')
        start=time.perf_counter();error=''
        with open(in_dir/f'{seed:04}.txt','rb') as inp:
            try:
                p=subprocess.run([str(tester),str(binaries[i])],stdin=inp,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,env=env,timeout=60)
                out,err=p.stdout,p.stderr
            except subprocess.TimeoutExpired as e:out,err=e.stdout or b'',e.stderr or b'';error='timeout (60s)'
        elapsed=time.perf_counter()-start
        publish(run_dirs[i]/'out'/f'{seed:04}.txt',out);publish(run_dirs[i]/'err'/f'{seed:04}.txt',err)
        scores=pahcer_run.SCORE_LINE.findall(err.decode(errors='replace'));score=int(scores[-1]) if scores and not error else 0
        if not error and not score:error=pahcer_run.judge_message(err.decode(errors='replace'))
        records[i]=dict(seed=seed,score=score,relative_score=0.,execution_time=elapsed,error_message=error,
                        arm=ARMS[i],source_seed=source_seed,design_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        input_sha256=hashlib.sha256((in_dir/f'{seed:04}.txt').read_bytes()).hexdigest(),
                        stdout_sha256=hashlib.sha256(out).hexdigest(),stderr_sha256=hashlib.sha256(err).hexdigest(),
                        stdout_bytes=len(out),stderr_bytes=len(err))
    return records

def main():
    global ARMS,DESIGNS,SOURCE_MAP
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--designs',type=Path,required=True)
    p.add_argument('--mapping',type=Path);p.add_argument('--arms',nargs='+',required=True);p.add_argument('--seeds',required=True);p.add_argument('--threads',type=int,default=4)
    p.add_argument('-c','--comment',default='joint pairing: frozen public-only designs; online time only')
    a=p.parse_args();ARMS=a.arms;DESIGNS=a.designs.resolve()
    SOURCE_MAP={int(k):int(v) for k,v in json.loads(a.mapping.read_text()).items()} if a.mapping else {}
    a.compare=[str(Path(__file__).parent)]*len(ARMS);a.no_record=True
    lo,hi=map(int,a.seeds.split('-'))
    template=tomllib.loads((ROOT/'pahcer_config.toml').read_text());template['test'].update(start_seed=lo,end_seed=hi,threads=a.threads)
    signal.signal(signal.SIGTERM,pahcer_run._raise_interrupted)
    pahcer_run.compare_case=compare_case
    # All arms compile the identical source snapshot; cache only after an actual
    # successful compile, with a content hash over every copied source file.
    real_compile=pahcer_run.compile_solution
    compiled={}
    def source_key(src):
        h=hashlib.sha256()
        for f in sorted(src.rglob('*')):
            if f.is_file():h.update(str(f.relative_to(src)).encode());h.update(f.read_bytes())
        return h.hexdigest()
    # A successful previous identical-source build is also reusable. Flags and
    # compiler identity must agree; the reported compile command remains reproducible.
    for old in sorted((ROOT/'runs').glob('*'),reverse=True):
        try:
            meta=json.loads((old/'meta.json').read_text())
            if meta.get('status')=='ok' and (old/'a.out').exists() and meta.get('compiler')==pahcer_run.compiler_version('g++') and meta['compile_command'][:4]==pahcer_run.COMPILE_CMD:
                compiled.setdefault(source_key(old/'src'),old/'a.out')
        except (OSError,ValueError,KeyError):pass
    def cached_compile(cmd,run_dir,src_root):
        h=hashlib.sha256()
        for f in sorted((run_dir/'src').rglob('*')):
            if f.is_file():h.update(str(f.relative_to(run_dir/'src')).encode());h.update(f.read_bytes())
        key=h.hexdigest()
        if key in compiled:
            shutil.copy2(compiled[key],run_dir/'a.out')
            (run_dir/'compile.log').write_text('Identical-source binary cache: '+key+'\n')
            return True
        ok=real_compile(cmd,run_dir,src_root)
        if ok:compiled[key]=run_dir/'a.out'
        return ok
    pahcer_run.compile_solution=cached_compile
    before=set((ROOT/'runs').glob('*'))
    ret=pahcer_run.evaluate_compare(a,ROOT,template)
    runs=sorted(x for x in (ROOT/'runs').glob('*') if x not in before and x.is_dir() and (x/'meta.json').exists())
    for run in runs:
        pth=run/'meta.json';j=json.loads(pth.read_text());idx=j['compare']['index'];j['research_arm']=ARMS[idx];j['design_time_excluded']=True
        pth.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
    (DESIGNS/f'evaluation-{lo}-{hi}.json').write_text(json.dumps(dict(arms=ARMS,runs=[x.name for x in runs],seeds=[lo,hi]),indent=2)+'\n')
    return ret
if __name__=='__main__':sys.exit(main())
