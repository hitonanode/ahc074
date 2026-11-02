"""Reproduce the whole-192-sheet, first-64-order legality check.

The official tester is used only to replay prepared, verified output against a
shortened input. No online performance or contest score is claimed.
"""
import sys
sys.dont_write_bytecode=True
import json,subprocess
from pathlib import Path
from resident_probe import Resident,HERE
from physical_trace import convert
from verify_model import verify

def main():
    work=HERE/'work';work.mkdir(exist_ok=True)
    data=Resident(0,28);verification=[]
    for kind in ('baseline','full'):
        prefix=work/f'physical0_{kind}';trace=prefix.with_suffix('.trace')
        p=subprocess.run([str(HERE/'long_module'),'2','1.0','28',str(trace)],
            input=data.make(kind,64,False),capture_output=True,text=True,check=True,timeout=180)
        assert p.stdout.strip().splitlines()[-1].startswith('ok,')
        verification.append(verify(trace));convert(0,kind,trace,prefix)
    (HERE/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    prefix=work/'physical0_full'
    with prefix.with_suffix('.in').open() as inp,prefix.with_suffix('.tester.err').open('w') as err:
        subprocess.run(['/home/sato/ahc074/tools/target/release/tester','python3',
            str(HERE/'serve_output.py'),str(prefix.with_suffix('.out'))],
            stdin=inp,stdout=subprocess.DEVNULL,stderr=err,check=True,timeout=30)
    print(prefix.with_suffix('.tester.err').read_text())

if __name__=='__main__':main()
