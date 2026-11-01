#!/usr/bin/env python3
"""Check the portable interactor's consequential protocol rules against replay.py."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from run_compare import capture_compare_case, checked_compare_case, portable_tester


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'scripts'))
    import replay
    tester = portable_tester(root)
    # These are interactor unit fixtures, not contestant benchmark runs.
    sample = '4 3 4 3\n1001\n1100\n0011\n0110\n0\n1\n2\n'
    designs = ['10.1', '1100', '0.1.']
    fixtures = [
        ('statement_example', sample, designs, ['0', '1\n0 2', '1\n1 2'], 2, False, False),
        ('all_wrong_cost', sample, designs, ['0', '0', '0'], 12, False, False),
        ('hidden_paper', sample, designs, ['1\n2 0'], 0, False, False),
        ('invisible_empty_paper', sample, ['10.1', '1100', '....'], ['1\n2 0'], 0, False, False),
        ('negative_count', sample, designs, ['-1'], 0, False, False),
        ('too_many_moves', sample, designs, ['7'], 0, False, False),
        ('paper_out_of_range', sample, designs, ['1\n3 0'], 0, False, False),
        ('depth_out_of_range', sample, designs, ['1\n0 3'], 0, False, False),
        ('bad_design', sample, ['10x1', '1100', '0.1.'], [], 0, False, False),
        ('extra_output', sample, designs, ['0', '1\n0 2', '1\n1 2'], 0, True, False),
        ('abnormal_exit', sample, designs, ['0', '1\n0 2', '1\n1 2'], 0, False, True),
        ('uncovered_is_white', '1 1 2 2\n0\n1\n0\n1\n', ['.'], ['0', '0'], 2, False, False),
    ]
    with tempfile.TemporaryDirectory(prefix='tester-check-', dir=root / 'runs') as work:
        work = Path(work)
        for name, test_input, papers, outputs, expected, extra, fail in fixtures:
            # Consume exactly one request before each reply. Invalid replies can
            # terminate the exchange early without waiting for later requests.
            script = work / f'{name}.py'
            script.write_text(
                'import sys\n'
                'n,k,p,r=map(int,input().split())\n'
                'for _ in range(p): input()\n'
                f'papers={papers!r}\n'
                'print("\\n".join(papers),flush=True)\n'
                f'outputs={outputs!r}\n'
                'for output in outputs:\n'
                '    request=input()\n'
                '    if request=="-1": sys.exit(0)\n'
                '    print(output,flush=True)\n'
                + ('print("0",flush=True)\n' if extra else '')
                + ('sys.exit(7)\n' if fail else '')
            )
            done = subprocess.run([str(tester), sys.executable, str(script)], input=test_input,
                                  text=True, capture_output=True, timeout=5)
            matches = re.findall(r'^Score = (\d+)$', done.stderr, re.MULTILINE)
            got = int(matches[-1]) if matches else None
            if got != expected:
                raise AssertionError((name, expected, got, done.stderr, done.stdout))
            inp = replay.parse_input(test_input)
            replayed = replay.replay(inp, replay.parse_output(inp, done.stdout), check=True)
            # A replay of stdout cannot detect a nonzero process exit code;
            # that fixture instead confirms the extra process-level check.
            if not fail and replayed.score != expected:
                raise AssertionError((name, 'replay disagreement', expected, replayed.score))

        # Check the information boundary using unbuffered stdin reads: the
        # interactor must withhold request 1 while request 0 is unanswered.
        script = work / 'request_boundary.py'
        script.write_text('''import os, select
def line():
    s=b''
    while not s.endswith(b'\\n'):
        x=os.read(0,1)
        if not x: raise RuntimeError('EOF')
        s+=x
    return s
n,k,p,r=map(int,line().split())
for _ in range(p): line()
os.write(1,b'.\\n')
assert line().strip()==b'0'
assert not select.select([0],[],[],0.02)[0], 'future request leaked'
os.write(1,b'0\\n')
assert line().strip()==b'1'
os.write(1,b'0\\n')
''')
        done = subprocess.run([str(tester), sys.executable, str(script)],
                              input='1 1 2 2\n0\n1\n0\n1\n', text=True,
                              capture_output=True, timeout=5)
        if done.returncode or 'Score = 2' not in done.stderr:
            raise AssertionError(('request_boundary', done.stderr))

        inputs = work / 'in'
        inputs.mkdir()
        (inputs / '0000.txt').write_text(sample)
        run = work / 'run'
        (run / 'out').mkdir(parents=True)
        (run / 'err').mkdir()
        complete = '\n'.join([*designs, '0', '1', '0 2', '1', '1 2']) + '\n'
        def simulated_runner(seed, order, binaries, in_dir, tester):
            return ([{'seed': 0, 'score': 2, 'execution_time': 0.1, 'error_message': ''}],
                    [{'out': complete.encode(), 'err': b'Score = 2\n'}])
        checked = checked_compare_case(simulated_runner, 0, [0], [None], [run], inputs, tester)
        assert checked[0]['artifact_verified'] and checked[0]['score'] == 2
        assert (run / 'out' / '0000.txt').read_text() == complete
        # Exercise simultaneous draining beyond the OS pipe buffer, using a
        # real reactive child. Whitespace is legal extra transport content.
        large = work / 'large_stream.py'
        large.write_text('#!' + sys.executable + '\n'
                         'import sys\n'
                         'n,k,p,r=map(int,input().split())\n'
                         'for _ in range(p): input()\n'
                         f'print({chr(10).join(designs)!r},flush=True)\n'
                         'for reply in ["0", "1\\n0 2", "1\\n1 2"]:\n'
                         '    input()\n'
                         '    print(reply,flush=True)\n'
                         'sys.stdout.write(" "*131072)\n'
                         'sys.stderr.write("x"*131072 + "\\n")\n')
        large.chmod(0o755)
        checked = checked_compare_case(capture_compare_case, 0, [0], [large], [run], inputs, tester)
        assert checked[0]['artifact_verified'] and checked[0]['score'] == 2
        assert (run / 'out' / '0000.txt').stat().st_size > 131072
        assert (run / 'err' / '0000.txt').stat().st_size > 131072
        def corrupt_runner(seed, order, binaries, in_dir, tester):
            records, captures = simulated_runner(seed, order, binaries, in_dir, tester)
            captures[0]['out'] = complete[:-5].encode()
            return records, captures
        checked = checked_compare_case(corrupt_runner, 0, [0], [None], [run], inputs, tester)
        assert not checked[0]['artifact_verified'] and checked[0]['score'] == 0
        assert checked[0]['adapter_score_before_verification'] == 2
        assert checked[0]['error_message'].startswith('artifact verification failed:')
    print(f'Passed {len(fixtures)} protocol/score fixtures, future-request boundary, pipe-buffer draining, and atomic-publication/fail-closed checks; replay.py agrees.')


if __name__ == '__main__':
    main()
