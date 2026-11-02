#!/usr/bin/env python3
"""Use the unchanged repository paired evaluator, with explicit portable-environment adapters."""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pahcer_run as runner
INPUT_DIR = ROOT / 'tools' / 'in'

def experiment_input(seed):
    return runner.replay.parse_input((INPUT_DIR / f'{seed:04d}.txt').read_text())

def atomic_bytes(path, data):
    pending = path.with_suffix(path.suffix + '.pending')
    with open(pending, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(pending, path)

def captured_compare_case(seed, order, binaries, run_dirs, in_dir, tester):
    """Publish complete transcripts atomically; never expose a running case's partial log."""
    data = (INPUT_DIR / f'{seed:04d}.txt').read_bytes()
    records = [{} for _ in binaries]
    for i in order:
        started = time.perf_counter()
        error = ''
        try:
            p = subprocess.run([str(tester), str(binaries[i])], input=data,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=runner.COMPARE_CASE_TIMEOUT)
            stdout, stderr = p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            stdout, stderr = e.stdout or b'', e.stderr or b''
            error = f'timeout ({runner.COMPARE_CASE_TIMEOUT:.0f} s)'
        elapsed = time.perf_counter() - started
        text = stderr.decode(errors='replace')
        scores = runner.SCORE_LINE.findall(text)
        score = int(scores[-1]) if scores and not error else 0
        if not error and score == 0: error = runner.judge_message(text)
        atomic_bytes(run_dirs[i] / 'out' / f'{seed:04d}.txt', stdout)
        atomic_bytes(run_dirs[i] / 'err' / f'{seed:04d}.txt', stderr)
        records[i] = {'seed': seed, 'score': score, 'relative_score': 0.0,
                      'execution_time': elapsed, 'error_message': error}
    return records

def main():
    global INPUT_DIR
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--portable-judge', action='store_true')
    ap.add_argument('--fixed', metavar='MAP,GOPT,ANNEAL,CLIMB')
    ap.add_argument('--input-dir', type=Path, default=INPUT_DIR,
                    help='Generated cases; existing official inputs need not be replaced')
    ap.add_argument('--compare', nargs='+')
    ap.add_argument('--extend', nargs='+')
    ap.add_argument('--seeds', default='0-32')
    ap.add_argument('-c', '--comment', default='')
    ap.add_argument('--no-record', action='store_true', default=True)
    args = ap.parse_args()
    args.solution = None
    INPUT_DIR = args.input_dir.resolve()
    runner.replay.load_input = experiment_input
    template = tomllib.loads((ROOT / 'pahcer_config.toml').read_text())
    template['test']['threads'] = args.threads
    runner.compare_case = captured_compare_case
    original_prepare = runner.prepare_run
    def prepare_with_context(*a, **kw):
        arm = original_prepare(*a, **kw)
        arm['meta']['input_directory'] = str(INPUT_DIR)
        arm['meta']['research_settings'] = {'fixed': args.fixed, 'threads': args.threads,
                                           'portable_judge': args.portable_judge,
                                           'environment': {k: os.environ[k] for k in
                                               ('RULE_STEPS', 'RULE_FULL', 'RULE_TWO', 'RULE_MAX_OPAQUE')
                                               if k in os.environ}}
        return arm
    runner.prepare_run = prepare_with_context
    original_compile_uncached = runner.compile_solution
    compiler = runner.compiler_version('g++') or 'g++'
    def cached_compile(command, run_dir, src_root):
        source = Path(command[-1]).read_bytes()
        flags = []
        skip = False
        for arg in command[:-1]:
            if skip:
                skip = False
                continue
            if arg == '-o':
                skip = True
                continue
            flags.append(arg)
        key = hashlib.sha256(source + ('\n' + compiler + '\n' + '\n'.join(flags)).encode()).hexdigest()
        cache = HERE / 'bin-cache' / key
        binary = Path(command[command.index('-o') + 1])
        if cache.exists():
            shutil.copy2(cache, binary)
            (run_dir / 'compile.log').write_text(f'Identical-source/flags/compiler cache: {key}\n')
            return True
        ok = original_compile_uncached(command, run_dir, src_root)
        if ok:
            cache.parent.mkdir(exist_ok=True)
            pending = cache.with_suffix('.pending')
            shutil.copy2(binary, pending)
            os.replace(pending, cache)
        return ok
    runner.compile_solution = cached_compile
    if args.portable_judge:
        judge = HERE / 'judge'
        src = HERE / 'judge.cpp'
        if not judge.exists() or judge.stat().st_mtime < src.stat().st_mtime:
            subprocess.run(['g++', '-std=c++23', '-O2', str(src), '-o', str(judge)], check=True)
        runner.ensure_tester = lambda root: judge
    if args.fixed:
        values = list(map(int, args.fixed.split(',')))
        if len(values) != 4: ap.error('--fixed requires four iteration counts')
        for k, v in zip(('MAP_ITERS', 'GOPT_STEPS', 'ANNEAL_ITERS', 'CLIMB_ITERS'), values):
            os.environ[k] = str(v)
        original_compile = runner.compile_solution
        def fixed_compile(command, run_dir, src_root):
            source = Path(command[-1]).read_text()
            # Exact copies except these online safeguards; do not edit the submission files.
            source, n1 = re.subn(r'kHelperGiveUp = 1\.55', 'kHelperGiveUp = 1000000.0', source)
            source, n2 = re.subn(r'kFastAfter = 1\.80', 'kFastAfter = 1000000.0', source)
            if n1 != 1 or n2 != 1:
                raise RuntimeError('Fixed-mode patch anchors not found exactly once')
            dest = run_dir / 'fixed-measurement.cpp'
            dest.write_text(source)
            patched = [*command[:-1], str(dest)]
            return original_compile(patched, run_dir, src_root)
        runner.compile_solution = fixed_compile
    args.comment += f' [portable={args.portable_judge}; threads={args.threads}; fixed={args.fixed}]'
    if args.extend:
        return runner.evaluate_extend(args, ROOT, template)
    if not args.compare or len(args.compare) < 2: ap.error('--compare needs at least two solutions')
    return runner.evaluate_compare(args, ROOT, template)

if __name__ == '__main__':
    raise SystemExit(main())
