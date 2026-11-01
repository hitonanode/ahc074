"""A valid N=64,K=192,P=256 instance family disproving universal return costs.
It is extremely atypical under the random generator, NOT a proposed solution
for random barcodes. Four independent four-pattern modules use private white
witnesses and a fixed 24-black-window background.
"""
import json
import random

patterns=[3,5,10,12]
fixed=((1<<24)-1)<<32
opaque=[(15<<(4*(k//4))) | (1<<(16+k)) for k in range(16)]+[fixed]+[0]*175
black=[patterns[k%4]<<(4*(k//4)) for k in range(16)]+[fixed]+[0]*175
targets=[fixed | sum(patterns[u>>(2*g)&3]<<(4*g) for g in range(4)) for u in range(256)]
assert len(set(targets))==256 and all(a.bit_count()==32 for a in targets)

def display(order):
    covered=shown=0
    visible=set()
    for k in order:
        mask=opaque[k]&~covered
        if mask:visible.add(k)
        shown|=black[k]&mask
        covered|=opaque[k]
    return shown,visible

rng=random.Random(749101)
operations=changed=0
for seq in range(8):
    order=list(range(192))
    prev_request=-1
    current=[0]*4
    for r in range(1024):
        u=rng.randrange(256 if r==0 else 255)
        if r and u>=prev_request:u+=1
        prev_request=u
        for g in range(4):
            t=u>>(2*g)&3
            if t==current[g]:continue
            k=4*g+t
            before,vis=display(order)
            assert k in vis
            order.remove(k);order.insert(0,k)
            after,_=display(order)
            changed+=(before^after).bit_count()
            operations+=1
            current[g]=t
        assert display(order)[0]==targets[u]

print(json.dumps(dict(papers=192,nonempty_papers=17,targets=256,ones_per_target=32,
                     verified_queries=8192,operations=operations,wrong=0,
                     exact_expected_moves_after_first=3*256/255,
                     exact_expected_moves_all_1024=(3+1023*3*256/255)/1024,
                     exact_changed_windows_per_nonzero_move=8/3,
                     sampled_moves_per_query=operations/8192,
                     sampled_changed_windows_per_move=changed/operations),indent=2))
