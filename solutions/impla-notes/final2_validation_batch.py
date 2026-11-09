"""Sequential recorded checks, with a stop on any failed safety or identity requirement."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];notes=Path(__file__).resolve().parent
for suite in ['identity_final','bounds','pattern','normal','stretch','judge']:
 print('BEGIN',suite,flush=True)
 with (notes/f'final2-{suite}.log').open('w') as out:
  subprocess.run([sys.executable,'-u',str(notes/'final2_suite.py'),suite],cwd=root,stdout=out,stderr=subprocess.STDOUT,check=True)
 with (notes/f'final2-{suite}-analysis.txt').open('w') as out:
  subprocess.run(['flock','-x','/home/sato/ahc074/runs/.lock','nice','-n','10',sys.executable,str(notes/'final2_analysis.py'),suite],cwd=root,stdout=out,stderr=subprocess.STDOUT,check=True)
 data=json.loads((notes/f'final2-{suite}.json').read_text())
 assert all(r['wa']==0 and not r['traps'] for r in data['runs']),suite+' failed safety'
 if 'identity' in data:assert all(x['same']==x['n']==200 for x in data['identity']),suite+' identity mismatch'
 if suite=='stretch':assert all(r['end_sec']['max']<=1.92 for r in data['runs']),suite+' exceeded hard end'
 print('PASS',suite,[r['run']for r in data['runs']],flush=True)
print('ALL CHECKS PASSED',flush=True)
