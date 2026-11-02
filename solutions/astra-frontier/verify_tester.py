#!/usr/bin/env python3
"""Check portable tester protocol and scoring against independent replay on small games."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import replay

GAME = '4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n'
BASE = "import sys\nfor _ in range(5): input()\nprint('10.1\\n1100\\n0011',flush=True)\n"
CASES = {
    'valid': BASE + "input(); print('0',flush=True)\ninput(); print('1\\n0 2',flush=True)\ninput(); print('1\\n1 2',flush=True)\n",
    'mistakes': BASE + "for _ in range(3):\n input(); print('0',flush=True)\n",
    'invisible': BASE + "input(); print('1\\n2 0',flush=True)\ninput()\n",
    'extra': BASE + "for _ in range(3):\n input(); print('0',flush=True)\nprint('99',flush=True)\n",
    'range': BASE + "input(); print('7',flush=True)\ninput()\n",
    'eof': BASE,
    'crash': BASE + "for _ in range(3):\n input(); print('0',flush=True)\nraise RuntimeError('deliberate fixture')\n",
}
EXPECTED = {'valid':2,'mistakes':12,'invisible':0,'extra':0,'range':0,'eof':0,'crash':0}

with tempfile.TemporaryDirectory(dir=ROOT / 'runs') as td:
    td = pathlib.Path(td)
    inpfile = td / 'fixture.txt'
    inpfile.write_text(GAME)
    inp = replay.parse_input(inpfile.read_text())
    rows = []
    for name, source in CASES.items():
        script = td / (name+'.py'); script.write_text(source)
        result = subprocess.run([str(ROOT/'tools/target/release/tester'),sys.executable,str(script)],
            input=GAME,text=True,capture_output=True,timeout=10)
        score = int(re.search(r'^Score = (\d+)$',result.stderr,re.M)[1])
        parsed = replay.parse_output(inp,result.stdout)
        replayed = replay.replay(inp,parsed)
        assert score == EXPECTED[name], (name,score,result.stderr)
        if name != 'crash':
            assert replayed.score == score, (name,score,replayed.score,replayed.error)
        rows.append({'case':name,'tester_score':score,'replay_score':replayed.score,
                     'replay_error':replayed.error})
    path = pathlib.Path(__file__).with_name('tester-checks.json')
    path.write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS',len(rows),'protocol/scoring fixtures')
