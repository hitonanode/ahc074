#!/usr/bin/env python3
"""Verify evaluator semantics on synthetic protocol fixtures; not a score benchmark."""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import replay


FIXTURE_SOLVER = '''import json,sys
fixture=json.load(open(sys.argv[1]))
n,k,p,r=map(int,sys.stdin.readline().split())
for _ in range(p): sys.stdin.readline()
print(fixture["design"],flush=True)
for response in fixture.get("responses",[]):
    line=sys.stdin.readline()
    if not line or line.strip()=="-1": break
    print(response,flush=True)
if "extra" in fixture: print(fixture["extra"],flush=True)
sys.exit(fixture.get("exit",0))
'''


def main():
    dest = HERE / "selftest-artifacts"
    dest.mkdir(exist_ok=True)
    solver = dest / "fixture_solver.py"
    solver.write_text(FIXTURE_SOLVER)
    result = []

    def check(name, inp_text, design, responses, expect_score, expect_error=None, extra=None, exitcode=0):
        fixture = {"design": design, "responses": responses}
        if extra is not None:
            fixture["extra"] = extra
        if exitcode:
            fixture["exit"] = exitcode
        path = dest / f"{name}.json"
        path.write_text(json.dumps(fixture))
        run = subprocess.run([str(ROOT / "tools/target/release/tester"), sys.executable, str(solver), str(path)],
                             input=inp_text, capture_output=True, text=True, timeout=5)
        (dest / f"{name}.in").write_text(inp_text)
        (dest / f"{name}.out").write_text(run.stdout)
        (dest / f"{name}.err").write_text(run.stderr)
        score = int(re.findall(r"Score = (\d+)", run.stderr)[-1])
        assert score == expect_score, (name, score, expect_score, run.stderr)
        relay_bytes = int(re.findall(r"tester_relay_bytes = (\d+)", run.stderr)[-1])
        assert relay_bytes == len(run.stdout.encode()), (name, relay_bytes, len(run.stdout.encode()))
        digest = 14695981039346656037
        for byte in run.stdout.encode():
            digest = ((digest ^ byte) * 1099511628211) & ((1 << 64) - 1)
        relay_digest = int(re.findall(r"tester_relay_fnv64 = ([0-9a-f]+)", run.stderr)[-1], 16)
        assert digest == relay_digest, (name, digest, relay_digest)
        if expect_error:
            assert expect_error in run.stderr, (name, run.stderr)
        else:
            inp = replay.parse_input(inp_text)
            out = replay.parse_output(inp, run.stdout)
            assert out.error is None, (name, out.error)
            game = replay.Game(inp, out.designs)
            for turn, operations in enumerate(out.queries):
                for paper, depth in operations:
                    game.move(paper, depth)
                game.finish(turn)
            assert game.score() == score, (name, game.score(), score)
        result.append({"name": name, "score": score, "expected_error": expect_error, "passed": True})

    sample_input = "4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n"
    check("statement-sample", sample_input, "10.1\n1100\n0.1.", ["0", "1\n0 2", "1\n1 2"], 2)
    check("invisible", sample_input, "1111\n0000\n....", ["1\n1 0"], 0, "Paper 1 is not visible")
    check("hole-paper", sample_input, "1111\n0000\n....", ["1\n2 0"], 0, "Paper 2 is not visible")
    check("count-range", sample_input, "1111\n0000\n....", ["7"], 0, "Out of range: 7")
    check("paper-range", sample_input, "1111\n0000\n....", ["1\n3 0"], 0, "Out of range: 3")
    check("depth-range", sample_input, "1111\n0000\n....", ["1\n0 3"], 0, "Out of range: 3")
    check("bad-pattern", sample_input, "111x\n0000\n....", [], 0, "Expected a paper pattern")
    check("bad-count", sample_input, "1111\n0000\n....", ["oops"], 0, "Parse error: oops")
    check("negative", sample_input, "1111\n0000\n....", ["-1"], 0, "Parse error: -1")
    check("eof", sample_input, "1111\n0000\n....", [], 0, "Unexpected EOF")
    check("extra", sample_input, "10.1\n1100\n0.1.", ["0", "1\n0 2", "1\n1 2"], 0,
          "Extra output after the last turn", extra="unexpected")
    check("crash", sample_input, "10.1\n1100\n0.1.", ["0", "1\n0 2", "1\n1 2"], 0,
          "Your program terminated abnormally", exitcode=1)
    check("uncovered-white", "4 1 2 2\n0000\n1111\n0\n1\n", "....", ["0", "0"], 2)
    rng = random.Random(75074)
    for test in range(30):
        n, k, p, r = 8, 12, 256, 24
        barcodes = [replay.mask_text(i, n) for i in range(p)]
        inp = replay.Input(n, k, p, r, barcodes, [0] * r)
        patterns = ["".join(rng.choices(".01", weights=[3, 1, 1], k=n)) for _ in range(k)]
        designs = [replay.Paper(s, replay.mask(s, "0") | replay.mask(s, "1"), replay.mask(s, "1")) for s in patterns]
        game = replay.Game(inp, designs)
        responses = []
        for turn in range(r):
            ops = []
            for _ in range(rng.randrange(0, 12)):
                visible = list(game.exposed())
                if not visible:
                    break
                paper = rng.choice(visible)
                depth = rng.randrange(k)
                ops.append((paper, depth))
                game.move(paper, depth)
            inp.requests[turn] = game.display() if rng.randrange(2) else rng.randrange(p)
            game.finish(turn)
            responses.append(str(len(ops)) + "\n" + "\n".join(f"{x} {d}" for x, d in ops))
        text = f"{n} {k} {p} {r}\n" + "\n".join(barcodes) + "\n" + "\n".join(map(str, inp.requests)) + "\n"
        check(f"random-{test:02d}", text, "\n".join(patterns), responses, game.score())
    (HERE / "selftest-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Passed {len(result)} tester protocol fixtures; 30 random trajectories independently checked by replay.Game.")


if __name__ == "__main__":
    main()
