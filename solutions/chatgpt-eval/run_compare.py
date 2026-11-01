#!/usr/bin/env python3
"""Run unchanged scripts/pahcer_run.py with an explicit portable tester and worker count."""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def portable_tester(root: Path) -> Path:
    source = Path(__file__).with_name('tester.cpp')
    binary = root / 'runs' / '.chatgpt-eval' / 'tester'
    binary.parent.mkdir(parents=True, exist_ok=True)
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(['g++', '-std=c++23', '-O2', '-o', str(binary), str(source)], check=True)
    return binary


def configure_template(cargs, root: Path, template: dict, jobs: int) -> None:
    """Allow an explicit fresh-case range without changing repository config."""
    template['test']['threads'] = jobs
    if cargs.seeds:
        matched = re.fullmatch(r'(\d+)-(\d+)', cargs.seeds)
        # Keep the original runner's validation and error for malformed ranges.
        if matched:
            first, end = map(int, matched.groups())
            if first < end:
                missing = [seed for seed in range(first, end)
                           if not (root / 'tools' / 'in' / f'{seed:04d}.txt').is_file()]
                if missing:
                    raise SystemExit(f'[chatgpt-eval] Missing input files for seeds: {missing[:12]}')
                template['test']['start_seed'] = min(template['test']['start_seed'], first)
                template['test']['end_seed'] = max(template['test']['end_seed'], end)


def atomic_write(path: Path, content: bytes) -> None:
    """Publish a complete artifact with a single rename in its final directory."""
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def capture_compare_case(seed, order, binaries, in_dir, tester):
    """Keep live stdout/stderr in pipes; do not reopen a live filesystem artifact.

    Seed ordering, binaries, limits and scoring conventions come from pahcer_run.
    Both pipes are drained by subprocess.communicate, so neither can block the
    reactive exchange when the output is larger than the OS pipe buffer.
    """
    import pahcer_run
    input_bytes = (in_dir / f'{seed:04d}.txt').read_bytes()
    records = [{} for _ in binaries]
    captures = [{} for _ in binaries]
    for index in order:
        error = ''
        started = time.perf_counter()
        try:
            done = subprocess.run([str(tester), str(binaries[index])], input=input_bytes,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=pahcer_run.COMPARE_CASE_TIMEOUT)
            output, stderr = done.stdout, done.stderr
            returncode = done.returncode
        except subprocess.TimeoutExpired as exc:
            output, stderr = exc.stdout or b'', exc.stderr or b''
            returncode = -1
            error = f'timeout ({pahcer_run.COMPARE_CASE_TIMEOUT:.0f} s)'
        elapsed = time.perf_counter() - started
        err_text = stderr.decode('utf-8', errors='replace')
        scores = pahcer_run.SCORE_LINE.findall(err_text)
        score = int(scores[-1]) if scores and not error and returncode == 0 else 0
        if not error and score == 0:
            error = pahcer_run.judge_message(err_text) or f'tester exit code {returncode}'
        records[index] = {'seed': seed, 'score': score, 'relative_score': 0.0,
                          'execution_time': elapsed, 'error_message': error}
        captures[index] = {'out': output, 'err': stderr}
    return records, captures


def checked_compare_case(capture, seed, order, binaries, run_dirs, in_dir, tester):
    """Verify captured bytes in memory, then publish complete files atomically."""
    import replay
    records, captures = capture(seed, order, binaries, in_dir, tester)
    inp = replay.parse_input((in_dir / f'{seed:04d}.txt').read_text())
    for index, run_dir in enumerate(run_dirs):
        record, captured = records[index], captures[index]
        failure = ''
        original_score = record['score']
        record['adapter_score_before_verification'] = original_score
        record['output_sha256'] = hashlib.sha256(captured['out']).hexdigest()
        record['stderr_sha256'] = hashlib.sha256(captured['err']).hexdigest()
        record['artifact_verified'] = False
        try:
            output = replay.parse_output(inp, captured['out'].decode('utf-8'))
            played = replay.replay(inp, output, check=True)
            record['artifact_replay_score'] = played.score
            record['artifact_replay_error'] = played.error
            verdicts = re.findall(rb'^Score = (\d+)\s*$', captured['err'], re.MULTILINE)
            if original_score > 0:
                if not verdicts or int(verdicts[-1]) != original_score:
                    failure = 'Captured stderr does not contain the recorded tester score'
                elif played.error or played.score != original_score or played.game.completed != inp.r:
                    failure = f'Replay score {played.score} != tester {original_score}: {played.error or "incomplete output"}'
                else:
                    record['artifact_verified'] = True
        except Exception as exc:
            failure = f'Cannot independently replay captured output: {exc}'
        if failure:
            record['score'] = 0
            record['error_message'] = f'artifact verification failed: {failure}'
            record['artifact_verification_failure'] = failure
        for stream in ('out', 'err'):
            atomic_write(run_dir / stream / f'{seed:04d}.txt', captured[stream])
    return records


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--official', action='store_true')
    parser.add_argument('--cxx-flag', action='append', default=[], help='Additional compiler flag, recorded in every run')
    args, forwarded = parser.parse_known_args()
    if args.jobs < 1:
        raise SystemExit('--jobs must be positive')
    if '--compare' not in forwarded and '--extend' not in forwarded and '-h' not in forwarded and '--help' not in forwarded:
        raise SystemExit('Use --compare or --extend (the unchanged single-run path requires pahcer).')
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'scripts'))
    import pahcer_run
    pahcer_run.COMPILE_CMD += args.cxx_flag
    details = {
        'tester': 'official-rust' if args.official else 'portable-cpp-adapter',
        'jobs': args.jobs,
        'clock_scale': 1.1,
        'extra_cxx_flags': args.cxx_flag,
        'experiment_environment': {key: os.environ[key] for key in (
            'MAP_ITERS', 'GOPT_STEPS', 'ANNEAL_ITERS', 'CLIMB_ITERS',
            'MULTIROUTE_LIMIT', 'MULTIROUTE_MIN_GAIN', 'REWIRE_LIMIT', 'REWIRE_MIN_GAIN',
            'RESCUE_Y', 'RESCUE_SUPPORT', 'RESCUE_EXACT_COST', 'RESCUE_LEARN_STEPS',
        ) if key in os.environ},
        'note': 'CLOCK_SCALE kept from the repository; this cloud host is not calibrated to AtCoder',
        'artifact_publication': 'pipe-capture-atomic-after-independent-replay-v2',
    }
    if not args.official:
        details['tester_source_sha256'] = hashlib.sha256(Path(__file__).with_name('tester.cpp').read_bytes()).hexdigest()
        pahcer_run.ensure_tester = portable_tester
    original_prepare = pahcer_run.prepare_run
    def prepare(*pargs, **kwargs):
        arm = original_prepare(*pargs, **kwargs)
        arm['meta']['chatgpt_evaluation'] = details
        pahcer_run.save_meta(arm['run_dir'], arm['meta'])
        return arm
    pahcer_run.prepare_run = prepare
    def compare_case(seed, order, binaries, run_dirs, in_dir, tester):
        return checked_compare_case(capture_compare_case, seed, order, binaries, run_dirs, in_dir, tester)
    pahcer_run.compare_case = compare_case
    # The repository's default is 0 (os.cpu_count); respect --jobs even when a
    # future config sets an explicit count, by changing the in-memory template.
    original_compare = pahcer_run.evaluate_compare
    original_extend = pahcer_run.evaluate_extend
    def compare(cargs, croot, template):
        configure_template(cargs, croot, template, args.jobs)
        return original_compare(cargs, croot, template)
    def extend(cargs, croot, template):
        configure_template(cargs, croot, template, args.jobs)
        return original_extend(cargs, croot, template)
    pahcer_run.evaluate_compare = compare
    pahcer_run.evaluate_extend = extend
    sys.argv = [str(root / 'scripts' / 'pahcer_run.py'), *forwarded]
    print(f'[chatgpt-eval] tester={details["tester"]}, jobs={args.jobs}; original comparison runner', file=sys.stderr)
    return pahcer_run.main()


if __name__ == '__main__':
    raise SystemExit(main())
