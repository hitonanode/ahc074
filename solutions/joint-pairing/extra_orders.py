#!/usr/bin/env python3
"""Seven extra held-out streams per problem; the design selection is never changed."""
import hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    mapping={};manifest=[]
    for i,seed in enumerate(range(6001,6033)):
        with open(ROOT/'tools/in'/f'{seed}.txt') as f:public=''.join(f.readline() for _ in range(257))
        for q in range(7):
            label=6200+7*i+q;rs=0xE079AB+2003*seed+12289*q;rng=random.Random(rs);prev=-1;requests=[]
            for _ in range(1024):
                x=rng.randrange(256 if prev<0 else 255)
                if prev>=0 and x>=prev:x+=1
                requests.append(x);prev=x
            text=public+''.join(f'{x}\n' for x in requests)
            (ROOT/'tools/in'/f'{label}.txt').write_text(text)
            mapping[label]=seed;manifest.append(dict(seed=label,source_seed=seed,request_rng_seed=rs,sha256=hashlib.sha256(text.encode()).hexdigest()))
    here=Path(__file__).parent
    (here/'extra-order-map.json').write_text(json.dumps(mapping,indent=2)+'\n')
    (here/'extra-order-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
