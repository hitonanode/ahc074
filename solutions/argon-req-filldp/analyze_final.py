from pathlib import Path
import subprocess,sys
prefix=sys.argv[1]
commands=[
['python3','solutions/argon-req-filldp/analyze.py',prefix+'_esw-slim',prefix+'_argon-req-filldp-positive','--json','solutions/argon-req-filldp/normal-final.json'],
['python3','solutions/argon-req-filldp/analyze.py','20261105-235755_argon-req-filldp-positive','20261105-235755_argon-req-filldp-joint-fast','--json','solutions/argon-req-filldp/zero-increment.json'],
['python3','solutions/argon-req-filldp/audit_final.py',prefix+'_esw-slim',prefix+'_argon-req-filldp-positive','20261105-235755_argon-req-filldp-positive'],
['python3','solutions/argon-req-filldp/analyze.py','20261105-234021_esw-slim','20261105-234021_argon-req-filldp','20261105-234021_argon-req-filldp-model','--json','solutions/argon-req-filldp/model-screen.json']]
for cmd in commands:
 print(' '.join(cmd),flush=True)
 subprocess.run(cmd,check=True)
