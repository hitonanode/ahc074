#!/usr/bin/env python3
"""Independently replay a solver output; optionally verify the 14 -> 14 -> 11 witness."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def masks(patterns: list[str]) -> tuple[list[int], list[int]]:
    assert len(patterns) == 192 and all(len(s) == 64 and set(s) <= set('01.') for s in patterns)
    return ([sum((c != '.') << j for j, c in enumerate(s)) for s in patterns],
            [sum((c == '1') << j for j, c in enumerate(s)) for s in patterns])


def replay(initial: list[int], path: list[list[int]], opaque: list[int], black: list[int], target: int) -> dict:
    order = initial.copy()
    assert sorted(order) == list(range(192))
    for step, (paper, depth) in enumerate(path):
        assert 0 <= paper < 192 and 0 <= depth < 192
        at = order.index(paper)
        exposed = opaque[paper]
        for other in order[:at]:
            exposed &= ~opaque[other]
        if not exposed:
            return dict(legal=False, step=step, invisible=paper)
        order.pop(at)
        order.insert(depth, paper)
    seen = view = 0
    owners: list[int | None] = [None] * 64
    for paper in order:
        exposed = opaque[paper] & ~seen
        for j in range(64):
            if (exposed >> j) & 1:
                owners[j] = paper
        view |= black[paper] & ~seen
        seen |= opaque[paper]
    wrong = [j for j in range(64) if ((view ^ target) >> j) & 1]
    return dict(legal=True, wrong=wrong, order=order, owners=owners)


def verify_output(inp: str, out: str) -> tuple[list[str], dict]:
    it = iter(inp.split())
    n, k, p, r = (int(next(it)) for _ in range(4))
    assert (n, k, p, r) == (64, 192, 256, 1024)
    targets = [int(next(it)[::-1], 2) for _ in range(p)]
    requests = [int(next(it)) for _ in range(r)]
    tokens = iter(out.split())
    patterns = [next(tokens) for _ in range(k)]
    opaque, black = masks(patterns)
    order = list(range(k))
    moves = 0
    for query, u in enumerate(requests):
        m = int(next(tokens))
        assert 0 <= m <= 2 * k
        path = [[int(next(tokens)), int(next(tokens))] for _ in range(m)]
        result = replay(order, path, opaque, black, targets[u])
        assert result['legal'], (query, result)
        assert not result['wrong'], (query, result['wrong'])
        order = result['order']
        moves += m
    assert next(tokens, None) is None, 'trailing output'
    return patterns, dict(orders=r, moves=moves, mean=moves / r, wrong=0, illegal=0)


def extract_witness(patterns: list[str], trace: str) -> dict:
    rows = trace.splitlines()
    marker = 'WITNESS 499 136 14 14 11'
    at = rows.index(marker)
    assert rows[at + 1].startswith('INITIAL ')
    witness = dict(seed=0, query=499, target=136, patterns=patterns,
                   target_bits='1111001000100011010100001101011011111011011000001011010101001010',
                   initial=list(map(int, rows[at + 1].split()[1:])))
    for offset, label in [(2, 'BEFORE'), (3, 'NEUTRAL'), (4, 'AFTER')]:
        fields = rows[at + offset].split()
        assert fields[0] == label
        witness[label.lower()] = [list(map(int, item.split(':'))) for item in fields[1:]]
    # The solver's final path additionally changes paper 100's insertion depth.
    # Undo just that change to demonstrate the deletion-only explanation.
    witness['simple_after'] = [[paper, 98 if paper == 100 else depth] for paper, depth in witness['after']]
    return witness


def verify_witness(witness: dict) -> None:
    opaque, black = masks(witness['patterns'])
    initial = witness['initial']
    target = int(witness['target_bits'][::-1], 2)
    for name, length in [('before', 14), ('neutral', 14), ('after', 11), ('simple_after', 11)]:
        result = replay(initial, witness[name], opaque, black, target)
        assert len(witness[name]) == length and result['legal'] and not result['wrong'], (name, result)
        print(f'{name}: {length} moves, legal and correct')

    # Delete edits by their stable anchors, not by stale numeric depths.
    order = initial.copy()
    edits = []
    for paper, depth in witness['neutral']:
        order.remove(paper)
        edits.append((paper, order[depth - 1] if depth else -1))
        order.insert(depth, paper)
    for removed in [{42}, {42, 82}, {42, 48}, {42, 82, 48}]:
        order, path = initial.copy(), []
        for paper, anchor in edits:
            if paper in removed:
                continue
            old = order.index(paper)
            order.pop(old)
            depth = order.index(anchor) + 1 if anchor >= 0 else 0
            order.insert(depth, paper)
            if old != depth:
                path.append([paper, depth])
        result = replay(initial, path, opaque, black, target)
        if removed == {42, 82}:
            assert not result['legal'] and result['invisible'] == 48
        elif removed == {42, 48}:
            assert result['legal'] and result['wrong'] == [26]
        else:
            assert result['legal'] and not result['wrong']
        summary = {key: value for key, value in result.items() if key not in {'order', 'owners'}}
        print(f'remove {sorted(removed)}: {summary}')
        if removed == {42, 82, 48}:
            assert path == witness['simple_after']
            assert result['owners'].count(117) == 11 and result['owners'][26] == 82
    print('paper 117 supplies 11 windows; retained paper 82 supplies window 26')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--trace', type=Path, help='TRACE_MAGIC=1 log for seed 0')
    parser.add_argument('--export-witness', type=Path, help='New path for readable complete witness JSON')
    args = parser.parse_args()
    if args.export_witness and not args.trace:
        parser.error('--export-witness requires --trace')
    patterns, result = verify_output(args.input.read_text(), args.output.read_text())
    print(json.dumps(result))
    if args.trace:
        witness = extract_witness(patterns, args.trace.read_text())
        verify_witness(witness)
        if args.export_witness:
            if args.export_witness.exists():
                parser.error('Witness export destination already exists')
            args.export_witness.write_text(json.dumps(witness, indent=2) + '\n')


if __name__ == '__main__':
    main()
