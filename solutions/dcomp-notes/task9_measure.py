"""One flock covers paired metrics and all stdout identity checks of a group."""
from pathlib import Path
import argparse,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('reference');p.add_argument('candidates',nargs='+')
p.add_argument('--seeds',default='0-500');a=p.parse_args();n=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(n/'metrics.py'),a.reference,*a.candidates,'--seeds',a.seeds,
                '--output',str(n/f't9-{a.tag}-metrics.json')],check=True)
for candidate in a.candidates:
    name=candidate.split('_',1)[1]
    subprocess.run([sys.executable,str(n/'identity.py'),a.reference,candidate,
                    '--output',str(n/f't9-{a.tag}-{name}-identity.json')],check=True)
