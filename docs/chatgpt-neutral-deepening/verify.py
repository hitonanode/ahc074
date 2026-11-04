#!/usr/bin/env python3
"""Independent physical replay. No solver metadata or state-value estimates."""
from pathlib import Path
import argparse, json

def masks(rows):
    if any(len(s) != 64 or set(s) - set('01.') for s in rows):
        raise ValueError('Invalid paper pattern')
    return ([sum((c != '.') << j for j, c in enumerate(s)) for s in rows],
            [sum((c == '1') << j for j, c in enumerate(s)) for s in rows])

def visible(order, k, opaque):
    exposed = opaque[k]
    for x in order:
        if x == k:
            return exposed
        exposed &= ~opaque[x]
    raise ValueError('Paper missing from stack')

def display(order, opaque, black):
    covered = view = 0
    for k in order:
        view |= black[k] & ~covered
        covered |= opaque[k]
    return view

def validate(inp, out):
    tokens = iter(inp.split())
    n, k, p, r = (int(next(tokens)) for _ in range(4))
    if (n, k, p, r) != (64, 192, 256, 1024):
        raise ValueError('Unexpected dimensions')
    targets = [int(next(tokens)[::-1], 2) for _ in range(p)]
    requests = [int(next(tokens)) for _ in range(r)]
    stream = iter(out.split())
    opaque, black = masks([next(stream) for _ in range(k)])
    order = list(range(k))
    moves = wrong = 0
    for request, product in enumerate(requests):
        count = int(next(stream))
        if not 0 <= count <= 2*k:
            raise ValueError(('Invalid operation count', request, count))
        for step in range(count):
            paper, depth = int(next(stream)), int(next(stream))
            if not (0 <= paper < k and 0 <= depth < k):
                raise ValueError(('Invalid operation', request, step))
            if not visible(order, paper, opaque):
                raise ValueError(('Invisible operation', request, step, paper))
            order.remove(paper)
            order.insert(depth, paper)
        moves += count
        wrong += display(order, opaque, black) != targets[product]
    if next(stream, None) is not None:
        raise ValueError('Trailing output')
    return dict(moves=moves, mean=moves/r, wrong=wrong, illegal=0)

def witness_check(path):
    w = json.loads(path.read_text())
    opaque, black = masks(w['papers'])
    target = int(w['target'][::-1], 2)
    def anchorize(path):
        order = w['initial'].copy()
        edits = []
        for k, d in path:
            order.remove(k)
            edits.append([k, order[d-1] if d else -1])
            order.insert(d, k)
        return edits
    def replay(edits):
        order = w['initial'].copy()
        illegal = []
        path = []
        access = []
        for step, (k, a) in enumerate(edits):
            pos = order.index(k)
            depth = order.index(a)+1 if a >= 0 else 0
            depth -= pos < depth
            if pos == depth:
                continue
            bits = visible(order, k, opaque)
            if not bits:
                illegal.append([step, k])
            if k == 8:
                access = [j for j in range(64) if bits >> j & 1]
            order.remove(k)
            order.insert(depth, k)
            path.append([k, depth])
        return dict(moves=len(path), illegal=illegal,
                    correct=display(order, opaque, black) == target,
                    access_for_paper8=access, path=path)
    original = anchorize(w['before'])
    i, j = w['swap_indices']
    first = [e[:] for e in original]
    first[i][1] = original[j][1]
    both = [e[:] for e in first]
    both[j][1] = original[i][1]
    dropped = [e for t, e in enumerate(original) if t != j]
    changed_and_dropped = [e for t, e in enumerate(first) if t != j]
    tests = {name: replay(edits) for name, edits in
             [('original', original), ('redirect_only', first), ('drop_only', dropped),
              ('swap_both', both), ('redirect_and_drop', changed_and_dropped)]}
    assert tests['original']['moves'] == 12 and not tests['original']['illegal']
    assert tests['redirect_only']['moves'] == 12 and not tests['redirect_only']['illegal']
    assert tests['drop_only']['illegal'], tests['drop_only']
    for name in ('swap_both', 'redirect_and_drop'):
        assert tests[name]['moves'] == 11 and not tests[name]['illegal'] and tests[name]['correct']
        assert tests[name]['access_for_paper8'] == [35, 42]
        assert tests[name]['path'] == w['after']
    assert all(t['correct'] for t in tests.values())
    return tests

def main():
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=root/'results')
    ap.add_argument('--inputs', type=Path, default=root/'inputs')
    ap.add_argument('--witness-only', action='store_true')
    args = ap.parse_args()
    witness = root/'witnesses/visibility_swap.json'
    if not witness.exists():
        witness = root/'visibility_swap.json'
    tests = witness_check(witness)
    report = dict(witness=tests)
    if not args.witness_only:
        paths = sorted(args.results.glob('*.out'))
        if not paths:
            raise SystemExit('No output files to verify')
        designs = {}
        total = 0
        for f in paths:
            seed = int(f.stem.rsplit('_', 1)[1])
            inp = (args.inputs/f'{seed:04d}.txt').read_text()
            out = f.read_text()
            result = validate(inp, out)
            assert result['wrong'] == result['illegal'] == 0, (str(f), result)
            expected = json.loads(f.with_suffix('.json').read_text())
            assert result['moves'] == expected['moves'], str(f)
            paper_rows = out.splitlines()[:192]
            assert designs.setdefault(seed, paper_rows) == paper_rows, ('Design mismatch', seed)
            total += result['moves']
        report.update(cases=len(paths), orders=len(paths)*1024, moves=total,
                      wrong=0, illegal=0, identical_design_seeds=len(designs))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.witness_only:
        (root/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
