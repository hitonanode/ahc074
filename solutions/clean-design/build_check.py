"""Compile the final source with both compilers, serialized against evaluations."""
from pathlib import Path
import fcntl,hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
source=HERE/'main.cpp'
with Path('/home/sato/ahc074/runs/.lock').open() as lock:
    fcntl.flock(lock,fcntl.LOCK_SH)
    snapshot=HERE/'check-source.cpp';snapshot.write_bytes(source.read_bytes())
    results=[]
    for compiler in ['/usr/bin/g++',shutil.which('clang++')]:
        for mode in ['judge','local','profilers']:
            name=('gcc' if compiler.endswith('g++') and 'clang' not in compiler else 'clang')+'-'+mode
            flags=[] if mode=='judge' else ['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
            if mode=='profilers':
                flags+=['-DAF_PROFILE=1','-DDESIGN_PROFILE=3','-DAS_PROFILE=1','-DCOLFAST_PROFILE=1',
                        '-DF3_PROFILE=1','-DSIM_HARNESS','-DPOSET_VERIFY']
            command=[compiler,'-std=c++23','-O2','-Wall','-Wextra',*flags,str(snapshot),'-o',str(HERE/('check-'+name))]
            p=subprocess.run(command,capture_output=True,text=True)
            (HERE/('check-'+name+'.log')).write_text(p.stdout+p.stderr)
            results.append({'name':name,'command':command,'exit_code':p.returncode,
                            'warnings':p.stderr.count('warning:'),'log':'check-'+name+'.log'})
            print(name,p.returncode,results[-1]['warnings'],flush=True)
    summary={'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'results':results}
    (HERE/'build-results.json').write_text(json.dumps(summary,indent=2)+'\n')
    assert all(x['exit_code']==0 and x['warnings']==0 for x in results)
