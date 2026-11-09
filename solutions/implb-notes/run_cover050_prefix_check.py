from pathlib import Path
import os,json,subprocess,sys
root=Path(__file__).resolve().parents[2]
env=dict(os.environ);env['JFLAGS_ARMS']=json.dumps([
 ['g++','-std=c++23 -O2'],
 ['g++','-std=c++23 -O2 -DNEXT_PREFIX_CHECK'],
 ['clang++','-std=c++23 -O2 -march=native -stdlib=libc++ -ftrivial-auto-var-init=zero -DNEXT_PREFIX_CHECK']])
with (root/'solutions/implb-notes/round3-cover-prefix-check.log').open('w') as f:
 subprocess.run([sys.executable,'solutions/jflags-notes/run.py','--compare','solutions/d30a-reset6','solutions/d30b-cover050','solutions/d30b-cover050','--design-from','20261109-130035_d30a-reset6','--seeds','0-20','--no-record','-c','B cover050 unchanged exact-bit NEXT_PREFIX_CHECK smoke GCC and Clang'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
