from pathlib import Path
import re
import subprocess
import sys

for name in sys.argv[1:]:
    log = Path(name)
    runs = list(dict.fromkeys(re.findall(r'run-id: (\S+)', log.read_text())))
    assert len(runs) >= 2, (name, runs)
    subprocess.run([sys.executable, 'solutions/argon-req-completeold/analyze.py', *runs,
                    '--json', str(log.with_suffix('.json'))], check=True)
    subprocess.run([sys.executable, 'solutions/argon-req-exactprofile/check_exact.py', *runs], check=True)
