import subprocess
commands=[
['python3','solutions/argon-req-filldp/analyze.py','20261105-234921_esw-slim','20261105-234921_argon-req-filldp-joint-fast','20261105-234921_argon-req-filldp-positive','20261105-234921_argon-req-filldp-jcharge','--json','solutions/argon-req-filldp/joint-screen.json'],
['python3','solutions/argon-req-filldp/check_saved.py','20261105-234500_argon-req-filldp-joint','20261105-234921_argon-req-filldp-joint-fast'],
['python3','solutions/argon-req-filldp/check_saved.py','20261105-235342_esw-slim','20261105-235342_argon-req-filldp-oracle'],
['python3','scripts/observe.py','cases','20261105-234921_argon-req-filldp-positive','--vs','20261105-234921_esw-slim','--top','4']]
for cmd in commands:
 print(' '.join(cmd),flush=True)
 subprocess.run(cmd,check=True)
