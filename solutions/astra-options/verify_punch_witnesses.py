#!/usr/bin/env python3
"""Independently verify helper_punch_g_probe witnesses by all 720 generic permutations."""
import argparse
import csv
import itertools
from pathlib import Path
import random

def mask(text, allowed):
    return sum((c in allowed) << j for j, c in enumerate(text))

def verify(input_path, output_path, csv_path, samples):
    tokens = Path(input_path).read_text().split()
    targets = [mask(s, '1') for s in tokens[4:260]]
    designs = Path(output_path).read_text().split()[:192]
    opaque = [mask(s, '01') for s in designs]
    black = [mask(s, '1') for s in designs]
    generic_mask = 0
    for value in opaque[:6]:
        generic_mask |= value
    handles = []
    columns = [-1]*192
    known = generic_mask
    for x in range(6, 192):
        fresh = opaque[x] & ~known
        handles += [j for j in range(64) if fresh >> j & 1]
        known |= opaque[x]
        columns[x] = max(c for c, j in enumerate(handles) if opaque[x] >> j & 1)
    permutations = list(itertools.permutations(range(6)))
    generic = []
    for order in permutations:
        covered = value = 0
        for x in order:
            value |= black[x] & ~covered
            covered |= opaque[x]
        generic.append(value)
    owners = [[u for u in range(256)
               if not ((targets[u] ^ black[x]) & opaque[x])
               and any(not ((g ^ targets[u]) & generic_mask & ~opaque[x]) for g in generic)]
              for x in range(192)]
    rows = list(csv.DictReader(Path(csv_path).open()))
    chosen = random.Random(74).sample(rows, min(samples, len(rows)))
    directions = 0
    for row in chosen:
        u, v, c = (int(row[s]) for s in ('u', 'v', 'c'))
        assert row['helper_u'] != row['helper_v']
        diff = targets[u] ^ targets[v]
        assert not (diff >> handles[c] & 1)
        gh = diff & generic_mask
        handle_prefix = sum(1 << j for j in handles[:c+1])
        hh = (~generic_mask & ((1 << 64)-1)) & (~handle_prefix | diff)
        for side, target in [('u', u), ('v', v)]:
            x = int(row['helper_'+side])
            prefix = int(row['prefix_'+side])
            g_bad = int(row['g_mask_'+side])
            h_bad = (black[x] ^ targets[target]) & opaque[x] & hh
            assert not (h_bad >> handles[columns[x]] & 1)
            assert h_bad.bit_count() == int(row['h_punch_'+side])
            assert g_bad.bit_count() == int(row['g_punch_'+side])
            prefix_opaque = 0
            for y in range(6):
                if prefix >> y & 1:
                    prefix_opaque |= opaque[y]
            expected_bad = (black[x] ^ targets[target]) & opaque[x] & gh & ~prefix_opaque
            assert expected_bad == g_bad
            new_opaque = opaque[x] & ~(g_bad | h_bad)
            new_black = black[x] & new_opaque
            depth = prefix.bit_count()
            feasible = False
            for order, g in zip(permutations, generic):
                if sum(1 << y for y in order[:depth]) != prefix:
                    continue
                shown = ((g & (prefix_opaque | ~new_opaque)) |
                         (new_black & generic_mask & ~prefix_opaque))
                if not ((shown ^ targets[target]) & gh):
                    feasible = True
                    break
            assert feasible, row
            assert not ((new_black ^ targets[target]) & new_opaque & hh), row
            for owner in owners[x]:
                assert any(not ((g ^ targets[owner]) & generic_mask & ~new_opaque)
                           for g in generic), (row, owner)
            directions += 1
    return directions

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('saved_output')
    parser.add_argument('witnesses_csv')
    parser.add_argument('--samples', type=int, default=100)
    args = parser.parse_args()
    n = verify(args.input, args.saved_output, args.witnesses_csv, args.samples)
    print(f'{n} direction witnesses, handle conditions, and every original helper owner verified')

if __name__ == '__main__':
    main()
