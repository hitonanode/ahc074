"""Confirm the premise of the white-background impossibility argument."""
from pathlib import Path
import json

root=Path('/home/sato/ahc074/tools/in')
all_variable=0;bad=[];fixed_zero=fixed_one=0
for seed in range(2000):
    with (root/f'{seed:04d}.txt').open() as f:
        n,k,p,r=map(int,f.readline().split())
        values=[int(f.readline().strip(),2) for _ in range(p)]
    union=0;intersection=(1<<n)-1
    for a in values:union|=a;intersection&=a
    zero=n-union.bit_count();one=intersection.bit_count()
    fixed_zero+=zero;fixed_one+=one
    if not zero and not one:all_variable+=1
    else:bad.append({'seed':seed,'fixed_zero':zero,'fixed_one':one})
result={'seeds':2000,'all_64_windows_variable':all_variable,'fixed_zero_windows':fixed_zero,'fixed_one_windows':fixed_one,'exceptions':bad}
Path(__file__).with_name('background.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
