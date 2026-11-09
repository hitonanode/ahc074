"""穴あけ前の分岐選択が変わる頻度と、選択一致時の出力同一性。"""
import argparse
import json
from pathlib import Path
import re

def analyze(base,candidate):
    root=Path('/home/sato/ahc074/runs');a=root/base;b=root/candidate
    ac={c['seed']:c for c in json.loads((a/'result.json').read_text())['cases']}
    bc={c['seed']:c for c in json.loads((b/'result.json').read_text())['cases']}
    same=[];different=[];unexpected=[];ambiguous=[];equal_out=0;available=0
    for seed in sorted(ac.keys()&bc.keys()):
        at=(a/'err'/f'{seed:04d}.txt').read_text();bt=(b/'err'/f'{seed:04d}.txt').read_text()
        values={int(i):float(v) for i,v in re.findall(r'^@deval_final ([0-3]) ([\d.eE+\-]+)$',at,re.M)}
        match=re.search(r'^perf_branch_chosen = (\d+)$',bt,re.M)
        if len(values)!=4 or not match:continue
        available+=1
        ranking=sorted(values,key=values.get);original=ranking[0];selected=int(match[1])
        equal=(a/'out'/f'{seed:04d}.txt').read_bytes()==(b/'out'/f'{seed:04d}.txt').read_bytes()
        equal_out+=equal
        # stderr's default precision is six significant digits. Avoid assigning
        # an exact winner when two printed V intervals may overlap.
        if values[ranking[1]]-values[ranking[0]]<=0.000100001:
            ambiguous.append(seed);continue
        if selected==original:
            same.append(seed)
            if not equal:unexpected.append(seed)
        else:different.append(seed)
    return {'base':base,'candidate':candidate,'cases':available,'same_branch':len(same),
            'different_branch':len(different),'different_branch_examples':different[:20],
            'identical_output':equal_out,'ambiguous_printed_V':ambiguous,
            'same_branch_but_different_output':unexpected}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--out',type=Path)
    args=p.parse_args();out=analyze(args.base,args.candidate)
    s=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if args.out:args.out.write_text(s)
    print(s)
