#!/usr/bin/env python3
"""指定テスターで交互計測する。ファイルはこのディレクトリの下だけに書く。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TESTER = Path('/home/sato/ahc074/tools/target/release/tester')


def run(binary, seed, prefix, counts):
    env = dict(os.environ, **{k: str(v) for k, v in counts.items()})
    started = time.monotonic()
    with (ROOT / 'tools' / 'in' / f'{seed:04}.txt').open('rb') as inp, \
            prefix.with_suffix('.out').open('wb') as out, \
            prefix.with_suffix('.err').open('wb') as err:
        result = subprocess.run([str(TESTER), str(HERE / binary)], stdin=inp,
                                stdout=out, stderr=err, env=env, check=False)
    metrics = dict(re.findall(r'^([A-Za-z_0-9]+) = ([-+0-9.eE]+)$',
                             prefix.with_suffix('.err').read_text(), re.M))
    metrics = {k: float(v) for k, v in metrics.items()}
    data = prefix.with_suffix('.out').read_bytes()
    record = dict(binary=binary, seed=seed, wall_sec=time.monotonic() - started,
                  returncode=result.returncode, sha256=hashlib.sha256(data).hexdigest(),
                  bytes=len(data), metrics=metrics, files=str(prefix.relative_to(HERE)))
    if result.returncode or metrics.get('Score', 0) <= 0:
        raise RuntimeError(record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binaries', nargs='+', default=['base', 'main'])
    parser.add_argument('--seeds', default='0')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--map', type=int, default=120000)
    parser.add_argument('--gopt', type=int, default=27200)
    parser.add_argument('--anneal', type=int, default=1024)
    parser.add_argument('--climb', type=int, default=-1)
    parser.add_argument('--label', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    counts = dict(MAP_ITERS=args.map, GOPT_STEPS=args.gopt,
                  ANNEAL_ITERS=args.anneal, CLIMB_ITERS=args.climb)
    dest = HERE / 'data' / args.label
    dest.mkdir(parents=True, exist_ok=False)
    records = []
    seeds = [int(x) for x in args.seeds.split(',')]
    for seed in seeds:
        for repeat in range(args.repeats):
            for binary in args.binaries:
                prefix = dest / f'{seed:04}-{repeat:02}-{binary}'
                row = run(binary, seed, prefix, counts)
                row['repeat'] = repeat
                records.append(row)
                (dest / 'results.json').write_text(json.dumps(dict(counts=counts, records=records), indent=2) + '\n')
                print(f"seed={seed} rep={repeat} bin={binary} map={row['metrics']['map_end_sec']:.6f} "
                      f"score={row['metrics']['Score']:.0f}", flush=True)
            if args.check:
                group = records[-len(args.binaries):]
                # SHA-256 に加えて全バイト列を直接比較する。
                contents = [(HERE / row['files']).with_suffix('.out').read_bytes() for row in group]
                if not all(x == contents[0] for x in contents):
                    raise RuntimeError(f'Output mismatch: seed={seed}, repeat={repeat}')
    for binary in args.binaries:
        times = [row['metrics']['map_end_sec'] for row in records if row['binary'] == binary]
        print(f'{binary}: median map_end_sec={statistics.median(times):.6f}', flush=True)


if __name__ == '__main__':
    main()
