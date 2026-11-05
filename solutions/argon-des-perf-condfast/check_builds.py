"""Four sequential builds; caller holds the evaluation lock through whenidle.sh."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=[]
for compiler in ['/usr/bin/g++','/usr/bin/clang++']:
    for local in [False,True]:
        name=('clang'if 'clang'in compiler else 'gcc')+('-local'if local else '-judge')
        command=[compiler,'-std=c++23','-O2','-Wall','-Wextra']
        if local:command+=['-DLOCAL_BENCH','-DCLOCK_SCALE=1.1']
        command+=[str(HERE/'main.cpp'),'-o',str(HERE/('check-'+name))]
        p=subprocess.run(command,capture_output=True,text=True)
        (HERE/('check-'+name+'.log')).write_text(p.stdout+p.stderr)
        row={'name':name,'exit':p.returncode,'warnings':p.stderr.count('warning:'),'command':command}
        rows.append(row);print(name,row['exit'],row['warnings'],flush=True)
(HERE/'build-results.json').write_text(json.dumps({'sha256':hashlib.sha256((HERE/'main.cpp').read_bytes()).hexdigest(),'results':rows},indent=2)+'\n')
assert all(r['exit']==0 and r['warnings']==0 for r in rows)
