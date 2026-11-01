#!/usr/bin/env python3
"""Focused tester correctness tests; these are protocol fixtures, not solver benchmarks."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TESTER = ROOT/'tools/target/release/tester'
SMALL = '1 2 2 1\n0\n1\n0\n'
SAMPLE = '4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n'

def run(name, input_text, code, expected, message=''):
    result = subprocess.run([str(TESTER), sys.executable, '-c', code], input=input_text,
                            text=True, capture_output=True, timeout=5)
    matches = re.findall(r'^Score = (\d+)$', result.stderr, re.M)
    assert matches and int(matches[-1]) == expected, (name, result)
    assert message in result.stderr, (name, result.stderr)
    return result

def fixed_output(text):
    return f'import sys; sys.stdout.write({text!r}); sys.stdout.flush()'

def main():
    count = 0
    run('published sample', SAMPLE, fixed_output('10.1\n1100\n0.1.\n0\n1 0 2\n1 1 2\n'), 2); count += 1
    run('wrong order costs 2K', SMALL, fixed_output('1\n0\n0\n'), 4); count += 1
    run('visible move works', SMALL, fixed_output('1\n0\n1\n0 1\n'), 1); count += 1
    run('hidden paper forbidden', SMALL, fixed_output('0\n1\n1\n1 0\n'), 0, 'not visible'); count += 1
    run('hole paper forbidden', SMALL, fixed_output('.\n0\n1\n0 1\n'), 0, 'not visible'); count += 1
    run('count bounds', SMALL, fixed_output('0\n1\n5\n'), 0, 'Out of range'); count += 1
    run('paper length', SMALL, fixed_output('00\n1\n0\n'), 0, 'Expected a paper'); count += 1
    run('early EOF', SMALL, fixed_output('0\n1\n'), 0, 'Unexpected EOF'); count += 1
    run('extra output', SMALL, fixed_output('0\n1\n0\n42\n'), 0, 'Extra output'); count += 1
    run('abnormal exit', SMALL, fixed_output('1\n0\n0\n')+'; sys.exit(3)', 0, 'terminated abnormally'); count += 1
    # Raw one-byte reads avoid Python prefetch masking a future request sent too early.
    code = '''
import os, select, sys
def line():
    b = b''
    while not b.endswith(b'\\n'):
        x = os.read(0, 1)
        assert x
        b += x
    return b
assert line().split() == [b'4', b'3', b'4', b'3']
for i in range(4): line()
assert not select.select([0], [], [], 0.01)[0], 'future request before design'
print('10.1\\n1100\\n0.1.', flush=True)
ops = ['0', '1\\n0 2', '1\\n1 2']
for r in range(3):
    assert int(line()) == r
    assert not select.select([0], [], [], 0.01)[0], 'future request before turn completion'
    print(ops[r], flush=True)
'''
    run('requests revealed one at a time', SAMPLE, code, 2); count += 1
    print(f'{count} tester protocol fixtures passed')

if __name__ == '__main__':
    main()
