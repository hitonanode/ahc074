#!/usr/bin/env python3
"""Exhaust the one-window generic gate neighborhood of a saved design."""
from __future__ import annotations
import argparse
import itertools
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"scripts"));import replay

def main():
    p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("seed",type=int);p.add_argument("--out",type=Path)
    args=p.parse_args();run=replay.resolve_run(args.run);inp=replay.load_input(args.seed)
    out=replay.parse_output(inp,(run/"out"/f"{args.seed:04d}.txt").read_text());papers=out.designs
    generic=0
    for x in papers[:6]:generic|=x.opaque
    orders=list(itertools.permutations(range(6)));all_states=(1<<720)-1
    displays=[]
    for order in orders:
        covered=black=0
        for k in order:black|=papers[k].black&~covered;covered|=papers[k].opaque
        displays.append(black)
    patterns=[]
    for cells in itertools.product(range(3),repeat=6):
        if not any(cells):continue
        bits=0
        for s,order in enumerate(orders):
            for k in order:
                if cells[k]:
                    bits|=(cells[k]==2)<<s
                    break
        patterns.append((cells,bits))
    holes=[]
    for target in inp.target:
        candidates=[k for k in range(6,inp.k) if ((target^papers[k].black)&papers[k].opaque)==0]
        assert len(candidates)==1,candidates
        holes.append(generic&~papers[candidates[0]].opaque)
    results=[];witness=set()
    for j in range(inp.n):
        if not generic>>j&1:continue
        old=tuple(0 if not papers[k].opaque>>j&1 else 2 if papers[k].black>>j&1 else 1 for k in range(6))
        edge=tuple(k for k in range(6) if old[k]);fixed=edge not in witness;witness.add(edge)
        goals=[]
        for t in range(inp.p):
            if holes[t]>>j&1:
                rest_mask=holes[t]&~(1<<j);rest=0
                for s,d in enumerate(displays):rest|=int(((d^inp.target[t])&rest_mask)==0)<<s
                goals.append((rest, bool(inp.target[t]>>j&1)))
        feasible=[]
        for cells,bits in patterns:
            if cells==old:continue
            if all(rest&(bits if color else all_states^bits) for rest,color in goals):feasible.append(cells)
        results.append({"window":j,"fixed_witness":fixed,"constrained_targets":len(goals),
                        "feasible_other_codes":len(feasible),"feasible_multiway_codes":sum(sum(c!=0 for c in cells)>2 for cells in feasible)})
    report={"run":run.name,"file_index":args.seed,"windows":results}
    print(json.dumps(report,indent=2))
    if args.out:args.out.write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__":main()
