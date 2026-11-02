#!/usr/bin/env python3
"""Protocol tests for the local tester; no candidate solution is benchmarked here."""
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay


SOLVER = r'''
import json, os, select, sys
data = json.load(open(sys.argv[1]))
def line():
    b = b''
    while not b.endswith(b'\n'):
        c = os.read(0, 1)
        if not c: return b.decode()
        b += c
    return b.decode()
n,k,p,r = map(int,line().split())
for _ in range(p): line()
assert not select.select([0], [], [], 0)[0], 'request sent before design'
print(data['design'], flush=True)
for response in data['queries']:
    request = line().strip()
    if request == '-1': sys.exit(0)
    assert request, 'missing query'
    assert not select.select([0], [], [], 0)[0], 'future request disclosed'
    print(response, flush=True)
if data.get('extra'):
    print(data['extra'], flush=True)
sys.exit(data.get('exit',0))
'''


def main():
    outdir = ROOT / "runs"
    outdir.mkdir(exist_ok=True)
    binary = outdir / ".chatgpt-tester"
    subprocess.run(["g++", "-std=c++23", "-O2", "-Wall", "-Wextra",
                    str(Path(__file__).with_name("tester.cpp")), "-o", str(binary)], check=True)
    tested = 0
    with tempfile.TemporaryDirectory(prefix="tester-selftest-", dir=outdir) as directory:
        tmp = Path(directory)
        solver = tmp / "solver.py"
        solver.write_text(SOLVER)

        def check(name, inp, data, expected, error=None):
            nonlocal tested
            config = tmp / "data.json"
            config.write_text(json.dumps(data))
            process = subprocess.run([str(binary), sys.executable, str(solver), str(config)],
                                     input=inp, text=True, capture_output=True, timeout=5)
            scores = re.findall(r"^Score = (\d+)$", process.stderr, re.M)
            assert scores and int(scores[-1]) == expected, (name, process.stderr)
            if error:
                assert error in process.stderr, (name, process.stderr)
            if not error:
                parsed = replay.parse_input(inp)
                output = replay.parse_output(parsed, process.stdout)
                assert not output.error, (name, output.error)
                game = replay.Game(parsed, output.designs)
                for r, operations in enumerate(output.queries):
                    for k, d in operations:
                        game.move(k, d)
                    game.finish(r)
                assert game.score() == expected, (name, game.score(), expected)
            tested += 1

        tiny = "4 3 3 3\n1001\n1100\n0011\n0\n1\n2\n"
        good = {"design": "10.1\n1100\n0.1.", "queries": ["0", "1\n0 2", "1\n1 2"]}
        check("statement example", tiny, good, 2)
        check("unicode whitespace", tiny, {**good, "queries": ["0", "1\n0\u30002", "1\n1\u00a02"]}, 2)
        check("extra output", tiny, {**good, "extra": "0"}, 0, "Extra output")
        check("abnormal exit", tiny, {**good, "exit": 7}, 0, "terminated abnormally")
        check("EOF before all queries", tiny, {**good, "queries": ["0"]}, 0, "Unexpected EOF")
        check("invisible", tiny, {**good, "design": "1111\n0000\n....", "queries": ["1\n1 0"]}, 0, "not visible")
        check("all hole move", tiny, {**good, "queries": ["1\n2 0"], "design": "....\n....\n...."}, 0, "not visible")
        check("move limit", tiny, {**good, "queries": ["7"]}, 0, "Out of range")
        check("paper range", tiny, {**good, "queries": ["1\n3 0"]}, 0, "Out of range")
        check("depth range", tiny, {**good, "queries": ["1\n0 3"]}, 0, "Out of range")
        check("bad integer", tiny, {**good, "queries": ["1.0"]}, 0, "Parse error")
        check("bad design", tiny, {**good, "design": "abcd\n1100\n0.1.", "queries": []}, 0, "Expected a paper pattern")
        check("wrong displays", tiny, {"design": "....\n....\n....", "queries": ["0", "0", "0"]}, 18)
        rng = random.Random(740)
        for case in range(10):
            n, k, p, r = 8, 9, 5, 30
            designs = ["".join(rng.choice("01...") for _ in range(n)) for _ in range(k)]
            targets = ["".join(rng.choice("01") for _ in range(n)) for _ in range(p)]
            requests = [rng.randrange(p) for _ in range(r)]
            text = f"{n} {k} {p} {r}\n" + "\n".join(targets + list(map(str, requests))) + "\n"
            inp = replay.parse_input(text)
            papers = [replay.Paper(s, replay.mask(s, "0") | replay.mask(s, "1"), replay.mask(s, "1")) for s in designs]
            game = replay.Game(inp, papers)
            queries = []
            for turn in range(r):
                operations = []
                for _ in range(rng.randrange(2 * k + 1)):
                    visible = list(game.exposed())
                    if not visible: break
                    paper, depth = rng.choice(visible), rng.randrange(k)
                    operations.append((paper, depth))
                    game.move(paper, depth)
                game.finish(turn)
                queries.append(str(len(operations)) + "\n" + "\n".join(f"{a} {b}" for a,b in operations))
            check(f"random replay {case}", text, {"design": "\n".join(designs), "queries": queries}, game.score())
    print(f"PASS: {tested} protocol/replay cases; no future queries disclosed; C++ tester agrees with Python replay")


if __name__ == "__main__":
    main()
