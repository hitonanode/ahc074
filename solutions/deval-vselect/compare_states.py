"""Compare saved physical states, excluding timing, logs and baseline metadata."""
from pathlib import Path
import argparse,json
RUNS=Path('/home/sato/ahc074/runs')
KEYS={'M','G','H','emergency','permutation','A','edge','polarity','papers','columns','ded','handle'}
def state(path):
    out={}
    for line in path.read_text().splitlines():
        name=line.partition(' ')[0]
        if name=='stderr':break
        if name in KEYS:out[name]=line
    assert {'M','G','H','papers','ded','A'}<=out.keys()
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate');p.add_argument('output')
    a=p.parse_args();x=RUNS/a.reference/'design';y=RUNS/a.candidate/'design'
    names=sorted(set(f.name for f in x.glob('*.txt'))&set(f.name for f in y.glob('*.txt')))
    wrong=[name for name in names if state(x/name)!=state(y/name)]
    output=dict(reference=a.reference,candidate=a.candidate,n=len(names),mismatches=wrong)
    Path(a.output).write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output))
if __name__=='__main__':main()
