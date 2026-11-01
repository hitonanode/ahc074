#!/usr/bin/env python3
"""Invoke the repository's unchanged paired evaluator, overriding only the in-memory thread count."""
import argparse
from pathlib import Path
import signal
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import pahcer_run

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--compare', nargs='+')
    parser.add_argument('--extend', nargs='+')
    parser.add_argument('--seeds')
    parser.add_argument('--no-record', action='store_true')
    parser.add_argument('-c', '--comment', default='')
    args = parser.parse_args()
    if bool(args.compare) == bool(args.extend):
        parser.error('Use exactly one of --compare and --extend')
    if args.threads < 1:
        parser.error('--threads must be positive')
    if args.compare and not args.no_record:
        parser.error('Fresh generated inputs require --no-record to avoid mixing official case histories')
    template = tomllib.loads((ROOT/'pahcer_config.toml').read_text())
    template['test']['threads'] = args.threads
    signal.signal(signal.SIGTERM, pahcer_run._raise_interrupted)
    if args.extend:
        return pahcer_run.evaluate_extend(args, ROOT, template)
    return pahcer_run.evaluate_compare(args, ROOT, template)

if __name__ == '__main__':
    sys.exit(main())
