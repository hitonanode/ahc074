#!/usr/bin/env python3
"""Focused checks of the portable judge: official example, penalty, hidden moves, extra output."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    judge = HERE / 'judge'
    if not judge.exists():
        subprocess.run(['g++', '-std=c++23', '-O2', str(HERE/'judge.cpp'), '-o', str(judge)], check=True)
    sample = '4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n'
    tests = [
        ('official-example', sample, ['10.1','1100','0.1.'], ['0','1\n0 2','1\n1 2'], '', 2),
        ('wrong-display-penalty', '1 2 1 1\n1\n0\n', ['0','1'], ['0'], '', 4),
        ('invisible-paper', '1 2 1 1\n0\n0\n', ['0','1'], ['1\n1 0'], '', 0),
        ('extra-output', '1 2 1 1\n0\n0\n', ['0','1'], ['0'], '0', 0),
        ('no-op-visible-move', '1 2 1 1\n0\n0\n', ['0','1'], ['1\n0 0'], '', 1),
    ]
    with tempfile.TemporaryDirectory(prefix='judge-fixtures-', dir=HERE) as td:
        solver = Path(td)/'fixture.py'
        for name, inp, papers, actions, extra, expected in tests:
            source = ('import sys\n'
                      'n,k,p,r=map(int,input().split())\n'
                      'for _ in range(p): input()\n'
                      f'print("\\n".join({papers!r}),flush=True)\n'
                      f'actions={actions!r}\n'
                      'for a in actions:\n'
                      ' q=input()\n'
                      ' if q=="-1": sys.exit()\n'
                      ' print(a,flush=True)\n'
                      f'extra={extra!r}\n'
                      'if extra: print(extra,flush=True)\n')
            solver.write_text(source)
            result = subprocess.run([str(judge), sys.executable, str(solver)], input=inp,
                                    text=True, capture_output=True, timeout=5)
            scores = re.findall(r'Score = (\d+)', result.stderr)
            assert scores and int(scores[-1]) == expected, (name, result.stderr)
            print(f'{name}: expected score {expected}, passed')

if __name__ == '__main__':
    main()
