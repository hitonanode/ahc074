from pathlib import Path
import json
import subprocess
import sys

def run(script, *args):
    subprocess.run([sys.executable, script, *args], check=True)

run('solutions/argon-req-exactprofile/collect.py',
    'solutions/argon-req-filterblocks/normal.log', 'solutions/argon-req-filterblocks/fixed-final.log')
run('solutions/argon-req-exactprofile/check_exact.py',
    '20261106-044522_argon-req-exactprofile', '20261106-044522_argon-req-filterblocks-profile')
run('solutions/argon-req-exactprofile/summarize.py',
    '20261106-044522_argon-req-exactprofile', '20261106-044522_argon-req-filterblocks-profile')
Path('solutions/argon-req-filterblocks-profile/profile-summary.json').write_bytes(
    Path('solutions/argon-req-exactprofile/profile-summary.json').read_bytes())
for item in json.loads(Path('solutions/argon-req-filterblocks/switch-runs.json').read_text()):
    print('Switches:', item['case'], item['env'], flush=True)
    run('solutions/argon-req-exactprofile/check_exact.py', *item['runs'])
    for name in item['runs']:
        text = Path('/home/sato/ahc074/runs', name, 'err', '0000.txt').read_text()
        if item['case'] == 'wide-trace': assert '#heavy ' in text and '#heavycand ' in text
        if item['case'] == 'uncached-mdpoff': assert 'colmdp_columns = 0' in text and 'f2_memo_hits = 0' in text
print('Old-base full comparisons, profilers, and switch checks passed.', flush=True)
