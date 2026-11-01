#!/usr/bin/env python3
"""Differential checks of the tester port against the independent replay module."""
from __future__ import annotations
import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))
import replay
from run_compare import build_tester

EMITTER = '''import json,sys
fixture=json.loads(sys.argv[1]); n,k,p,r=map(int,input().split())
for _ in range(p): input()
print(fixture["design"],flush=True)
for text in fixture["queries"]:
    q=input()
    if q=="-1": sys.exit()
    print(text,flush=True)
if fixture.get("extra"): print(fixture["extra"],flush=True)
sys.exit(fixture.get("exit",0))
'''

def text_of(inp: replay.Input) -> str:
    return f"{inp.n} {inp.k} {inp.p} {inp.r}\n" + "\n".join(inp.barcodes + list(map(str, inp.requests))) + "\n"

def expected(inp: replay.Input, output: str) -> tuple[int, str | None]:
    parsed = replay.parse_output(inp, output)
    if parsed.error: return 0, parsed.error
    game = replay.Game(inp, parsed.designs)
    try:
        for r, ops in enumerate(parsed.queries):
            for k, d in ops: game.move(k, d)
            game.finish(r)
    except replay.InvalidMove as e: return 0, str(e)
    return game.score(), None

def main() -> None:
    binary = build_tester(ROOT)
    rng = random.Random(74002026)
    fixtures = []
    # Random legal operations exercise all insertion depths, no-op moves, partial
    # exposure, holes, and accumulated mistaken requests.
    for index in range(40):
        n, k, p, r = 8, 11, 4, 17
        inp = replay.Input(n, k, p, r,
            ["".join(rng.choice("01") for _ in range(n)) for _ in range(p)],
            [rng.randrange(p) for _ in range(r)])
        patterns = ["".join(rng.choices(".01", weights=[6,1,1], k=n)) for _ in range(k)]
        papers = [replay.Paper(s, replay.mask(s,"0") | replay.mask(s,"1"), replay.mask(s,"1")) for s in patterns]
        game = replay.Game(inp, papers)
        queries = []
        for q in range(r):
            ops = []
            for _ in range(rng.randrange(2*k + 1)):
                visible = list(game.exposed())
                if not visible: break
                a, d = rng.choice(visible), rng.randrange(k)
                game.move(a, d); ops.append((a,d))
            game.finish(q)
            queries.append(str(len(ops)) + "\n" + "\n".join(f"{a} {d}" for a,d in ops))
        fixtures.append((f"random_legal_{index}",inp,{"design":"\n".join(patterns),"queries":queries}))
    inp = replay.Input(4,3,3,3,["1001","1100","0011"],[0,1,2])
    fixtures.append(("statement_example",inp,{"design":"10.1\n1100\n0.1.","queries":["0","1\n0 2","1\n1 2"]}))
    for name, design, queries, extra, exit_code in [
        ("invisible", "0000\n1111\n....", ["1\n1 0"], "",0),
        ("all_holes_invisible", "....\n....\n....", ["1\n0 0"], "",0),
        ("out_of_range_paper", "0000\n1111\n....", ["1\n3 0"], "",0),
        ("out_of_range_depth", "0000\n1111\n....", ["1\n0 3"], "",0),
        ("too_many_moves", "0000\n1111\n....", ["7"], "",0),
        ("negative_moves", "0000\n1111\n....", ["-1"], "",0),
        ("invalid_pattern", "00x0\n1111\n....", [], "",0),
        ("extra_output", "0000\n1111\n....", ["0","0","0"], "0",0),
        ("runtime_error", "0000\n1111\n....", ["0","0","0"], "",3),
        ("background_white", "....\n....\n....", ["0","0","0"], "",0),
    ]:
        fixtures.append((name,inp,{"design":design,"queries":queries,"extra":extra,"exit":exit_code}))
    results = []
    for name, inp, fixture in fixtures:
        output = fixture["design"] + "\n" + "\n".join(fixture["queries"]) + "\n" + fixture.get("extra","")
        score, error = expected(inp,output)
        if fixture.get("exit"): score,error = 0,"Your program terminated abnormally"
        run = subprocess.run([str(binary),sys.executable,"-c",EMITTER,json.dumps(fixture)],
                             input=text_of(inp),text=True,capture_output=True,timeout=5)
        found = re.findall(r"(?m)^Score = (\d+)$",run.stderr)
        assert found and int(found[-1]) == score, (name,score,error,run.stderr)
        if error:
            # When a transcript ends immediately after an invalid move, the
            # replay parser can report EOF before replaying. The online tester
            # correctly diagnoses that move first; both must reject the case.
            assert score == 0 and len(run.stderr.splitlines()) > 1, (name,run.stderr)
        else:
            assert run.stderr.strip() == f"Score = {score}", (name,run.stderr)
            assert run.stdout.split() == output.split(), (name,"relay changed tokens")
        results.append({"name":name,"expected_score":score,"actual_score":int(found[-1]),"rejected":error is not None})
    report = {"checks":len(results),"passed":len(results),"oracle":"scripts/replay.py",
              "tester_sha256":hashlib.sha256((HERE/"tester.cpp").read_bytes()).hexdigest(),"results":results}
    (HERE/"tester_checks.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"{len(results)} tester checks passed (40 randomized legal transcripts plus protocol/visibility cases)")

if __name__ == "__main__": main()
