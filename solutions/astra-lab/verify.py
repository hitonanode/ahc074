#!/usr/bin/env python3
"""Independently replay every move, including visibility, using the run's selected input directory."""
import argparse
import concurrent.futures
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import replay

def check(job):
    input_path, output_path, expected = job
    inp = replay.parse_input(Path(input_path).read_text())
    out = replay.parse_output(inp, Path(output_path).read_text())
    rep = replay.replay(inp, out, check=True)
    ok = rep.error is None and len(rep.queries) == inp.r and rep.score == expected
    return ok, rep.error, rep.score

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--processes', type=int, default=4)
    ap.add_argument('--seeds', help='Optional START-END (END excluded)')
    args = ap.parse_args()
    selected = None
    if args.seeds:
        start, end = map(int, args.seeds.split('-'))
        selected = set(range(start, end))
    failed = []
    for name in args.runs:
        run = ROOT / 'runs' / name
        meta = json.loads((run / 'meta.json').read_text())
        result = json.loads((run / 'result.json').read_text())
        cases = [c for c in result['cases'] if selected is None or c['seed'] in selected]
        inputs = Path(meta.get('input_directory', ROOT / 'tools' / 'in'))
        jobs = [(str(inputs / f"{c['seed']:04d}.txt"),
                 str(run / 'out' / f"{c['seed']:04d}.txt"), c['score']) for c in cases]
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.processes) as pool:
            outcomes = list(pool.map(check, jobs))
        bad = [{'seed': case['seed'], 'error': outcome[1], 'replay_score': outcome[2]}
               for case, outcome in zip(cases, outcomes) if not outcome[0]]
        print(f'{name}: {len(outcomes)-len(bad)}/{len(outcomes)} exact scores and legal moves')
        if bad: failed.append({'run': name, 'cases': bad})
    if failed:
        print(json.dumps(failed, ensure_ascii=False, indent=2))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
