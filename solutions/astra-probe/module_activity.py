"""How often 3 consecutive handle windows are exposed by the designated top.
This is a workload count, not a simulation of the proposed module controller.
"""
import csv
import sys
from analyze import load

out=csv.writer(sys.stdout)
out.writerow(['seed','block','columns','papers','access_probability','full_hole_probability','partial_hole_probability','rho_if_full_holes_only'])
for seed in range(8):
    inp,trace,gm,hs,cols,serves=load(seed)
    ps=trace.designs
    ded={u:k for k,us in serves.items() for u in us}
    for b in range(9):
        cc=list(range(3*b,3*b+3))
        mask=sum(1 << hs[c] for c in cc)
        access=full=partial=0
        for u in range(256):
            k=ded[u]
            access += cols[k] in cc
            holes=(mask & ~ps[k].opaque).bit_count()
            full += holes==3
            partial += 0<holes<3
        out.writerow([seed,b,':'.join(map(str,cc)),sum(cols[k] in cc for k in range(6,192)),access/256,full/256,partial/256,access/(access+full) if access+full else 0])
