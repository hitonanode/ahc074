from pathlib import Path
import subprocess,json
P=Path(__file__).resolve().parent
rows=[]
for c in ['g++','clang++']:
 binary=P/('verify-quotient-'+c.replace('+','p'))
 cmd=[c,'-std=c++23','-O2',str(P/'verify_quotient.cpp'),'-o',str(binary)]
 subprocess.run(cmd,check=True)
 p=subprocess.run([str(binary)],text=True,capture_output=True)
 binary.unlink()
 rows.append({'compiler':c,'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 print(c,p.stdout,flush=True)
(P/'quotient-verification.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(x['returncode']==0 for x in rows)
