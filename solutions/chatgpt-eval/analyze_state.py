#!/usr/bin/env python3
"""Inspect initial query visibility and dedicated-paper access in saved outputs."""
from __future__ import annotations
import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import replay

def mean(xs): return statistics.mean(xs) if xs else None

def main():
    p=argparse.ArgumentParser();p.add_argument("run");p.add_argument("--out",type=Path)
    args=p.parse_args();run=replay.resolve_run(args.run)
    data=collections.defaultdict(list); counts=collections.Counter(); details=[]
    for seed in replay.run_scores(run):
        inp=replay.load_input(seed)
        out=replay.parse_output(inp,(run/"out"/f"{seed:04d}.txt").read_text())
        game=replay.Game(inp,out.designs)
        candidates=[[k for k,paper in enumerate(out.designs) if k>=6 and
            ((paper.black^target)&paper.opaque)==0] for target in inp.target]
        target_weight=[0]*inp.k
        for cs in candidates:
            for k in cs: target_weight[k]+=1
        for r,ops in enumerate(out.queries):
            target=inp.target[inp.requests[r]]; cs=candidates[inp.requests[r]]
            visible=game.exposed();data["visible_papers"].append(len(visible))
            data["accessible_future_products"].append(sum(target_weight[k] for k in visible))
            data["target_paper_visible"].append(any(k in visible for k in cs))
            data["dedicated_candidates"].append(len(cs))
            if cs:
                lower=[]
                for k in cs:
                    coverers=[0]*inp.n
                    for j in game.order[:game.position(k)]:
                        opq=out.designs[j].opaque
                        while opq:
                            low=opq&-opq; coverers[low.bit_length()-1]+=1; opq-=low
                    lower.append(min(coverers[j] for j in range(inp.n) if out.designs[k].opaque>>j&1))
                data["coverer_count_to_expose_target"].append(min(lower))
            direct=generic=other=neutral=positive=negative=0
            for k,d in ops:
                if k<6: generic+=1
                elif k in cs: direct+=1
                else: other+=1
                before=game.display();before_wrong=(before^target).bit_count()
                game.move(k,d);after=game.display();after_wrong=(after^target).bit_count()
                neutral += before==after
                positive += after_wrong<before_wrong
                negative += after_wrong>before_wrong
            data["generic_moves"].append(generic);data["target_paper_moves"].append(direct)
            data["other_paper_moves"].append(other);data["display_unchanged_moves"].append(neutral)
            data["hamming_reducing_moves"].append(positive);data["hamming_increasing_moves"].append(negative)
            data["target_paper_used"].append(direct>0)
            data["generic_moves_pair" if cs and target_weight[cs[0]]==2 else "generic_moves_single"].append(generic)
            counts["queries"]+=1;counts["moves"]+=len(ops)
            assert game.finish(r)
        details.append({"file_index":seed,"score":game.score()})
    report={"run":run.name,"cases":len(details),"queries":counts["queries"],
            "mean_per_query":{k:mean(v) for k,v in data.items()},"case_scores":details}
    print(json.dumps(report,indent=2))
    if args.out:args.out.write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__":main()
