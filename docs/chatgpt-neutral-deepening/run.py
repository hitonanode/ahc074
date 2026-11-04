#!/usr/bin/env python3
"""Fixed-work local research only; not an official pahcer or judge run."""
from pathlib import Path
import argparse, json, os, subprocess, time
from verify import validate

def main() -> None:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument('method', choices=['control', 'prior', 'permutation', 'portal'])
    ap.add_argument('start', type=int, nargs='?', default=0)
    ap.add_argument('end', type=int, nargs='?', default=40)
    ap.add_argument('--source-dir', type=Path, default=root / 'sources')
    ap.add_argument('--input-dir', type=Path, default=root / 'inputs')
    ap.add_argument('--output-dir', type=Path, default=root / 'reruns')
    args = ap.parse_args()
    if not 0 <= args.start < args.end:
        raise SystemExit('Expected 0 <= start < end.')
    binary = root / 'build' / args.method
    binary.parent.mkdir(exist_ok=True)
    subprocess.run(['g++', '-O2', '-std=c++23', '-march=native',
                    str(args.source_dir / (args.method + '.cpp')), '-o', str(binary)], check=True)
    env = dict(os.environ, BENCH_FIXED='1', MAP_ITERS='160000', GOPT_STEPS='60000',
               ANNEAL_ITERS='10000000', CLIMB_ITERS='16000', PATCH_ITERS='3000',
               NEUTRAL_DEPTH='2', NEUTRAL_WIDTH='4', NEUTRAL_SIGNATURE='0',
               NEUTRAL_MARGIN='0.75', NEUTRAL_ROUNDS='1', REROUTE_ALL='0',
               REROUTE_ONLY='0', SWAP_EDITS='0', SWAP_ONLY='0', CACHE_POST='0', PORTAL_GROUP='0')
    if args.method == 'permutation':
        env.update(NEUTRAL_ROUNDS='3', REROUTE_ALL='1', SWAP_EDITS='1', CACHE_POST='1')
    elif args.method == 'portal':
        env['PORTAL_GROUP'] = '2'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for seed in range(args.start, args.end):
        inp = (args.input_dir / f'{seed:04d}.txt').read_text()
        start = time.perf_counter()
        p = subprocess.run([str(binary)], input=inp, text=True, capture_output=True,
                           env=env, check=True, timeout=120)
        seconds = time.perf_counter() - start
        result = validate(inp, p.stdout)
        if result['wrong'] or result['illegal']:
            raise RuntimeError((args.method, seed, result))
        result.update(method=args.method, seed=seed, seconds=seconds)
        for ext, content in [('out', p.stdout), ('log', p.stderr),
                             ('json', json.dumps(result, indent=2))]:
            (args.output_dir / f'{args.method}_{seed}.{ext}').write_text(content)
        print(args.method, seed, result['moves'], seconds, flush=True)

if __name__ == '__main__':
    main()
