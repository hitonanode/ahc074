#!/usr/bin/env python3
"""Compare the learner's greedy failure with exact maximum-cardinality matching.

This reads completed runs only. It is analysis, not a solver, and does not expose
future requests to a submitted program. No third-party package is required.
"""
import argparse
import functools
import itertools
import json
from pathlib import Path
import random


def maximum_matching(adj):
    """Edmonds' augmenting-path algorithm with contraction of odd blossoms."""
    n = len(adj)
    mate = [-1] * n
    for root in range(n):
        if mate[root] >= 0:
            continue
        parent = [-1] * n
        base = list(range(n))
        used = [False] * n
        used[root] = True
        queue = [root]

        def lca(a, b):
            seen = [False] * n
            while True:
                a = base[a]
                seen[a] = True
                if mate[a] < 0:
                    break
                a = parent[mate[a]]
            while True:
                b = base[b]
                if seen[b]:
                    return b
                b = parent[mate[b]]

        endpoint = -1
        at = 0
        while at < len(queue) and endpoint < 0:
            v = queue[at]
            at += 1
            for u in adj[v]:
                if base[v] == base[u] or mate[v] == u:
                    continue
                if u == root or (mate[u] >= 0 and parent[mate[u]] >= 0):
                    common = lca(v, u)
                    blossom = [False] * n

                    def mark_path(x, child):
                        while base[x] != common:
                            blossom[base[x]] = blossom[base[mate[x]]] = True
                            parent[x] = child
                            child = mate[x]
                            x = parent[mate[x]]

                    mark_path(v, u)
                    mark_path(u, v)
                    for x in range(n):
                        if blossom[base[x]]:
                            base[x] = common
                            if not used[x]:
                                used[x] = True
                                queue.append(x)
                elif parent[u] < 0:
                    parent[u] = v
                    if mate[u] < 0:
                        endpoint = u
                        break
                    used[mate[u]] = True
                    queue.append(mate[u])
        if endpoint >= 0:
            v = endpoint
            while v >= 0:
                previous = parent[v]
                following = mate[previous] if previous >= 0 else -1
                mate[v] = previous
                if previous >= 0:
                    mate[previous] = v
                v = following
    return sum(x >= 0 for x in mate) // 2


def self_check():
    rng = random.Random(7784129)
    for n in range(2, 11):
        for _ in range(30):
            adj = [[] for _ in range(n)]
            for a in range(n):
                for b in range(a + 1, n):
                    if rng.random() < 0.35:
                        adj[a].append(b)
                        adj[b].append(a)

            @functools.cache
            def brute(mask):
                if not mask:
                    return 0
                bit = mask & -mask
                v = bit.bit_length() - 1
                rest = mask ^ bit
                return max([brute(rest)] + [1 + brute(rest ^ (1 << u)) for u in adj[v] if rest >> u & 1])

            assert maximum_matching(adj) == brute((1 << n) - 1)


def analyze(run, input_dir, seed):
    tokens = (input_dir / f"{seed:04d}.txt").read_text().split()
    patterns = [int(s[::-1], 2) for s in tokens[4:260]]
    rows = (run / "out" / f"{seed:04d}.txt").read_text().splitlines()[:6]
    opaque = [sum((ch != ".") << j for j, ch in enumerate(row)) for row in rows]
    black = [sum((ch == "1") << j for j, ch in enumerate(row)) for row in rows]
    mask = functools.reduce(int.__or__, opaque, 0)
    windows = [j for j in range(64) if mask >> j & 1]
    truth = {j: [0, 0] for j in windows}
    for state, order in enumerate(itertools.permutations(range(6))):
        covered = colour = 0
        for k in order:
            colour |= black[k] & ~covered
            covered |= opaque[k]
        for j in windows:
            truth[j][colour >> j & 1] |= 1 << state
    adj = [[] for _ in range(256)]
    for u in range(256):
        for v in range(u + 1, 256):
            diff = patterns[u] ^ patterns[v]
            if diff.bit_count() > 26:
                continue
            holes = diff & mask
            left = right = (1 << 720) - 1
            while holes and left and right:
                bit = holes & -holes
                holes -= bit
                j = bit.bit_length() - 1
                colour = patterns[u] >> j & 1
                left &= truth[j][colour]
                right &= truth[j][1 - colour]
            if left and right:
                adj[u].append(v)
                adj[v].append(u)
    size = maximum_matching(adj)
    return {
        "seed": seed,
        "close_edges": sum(map(len, adj)) // 2,
        "maximum_matching_size": size,
        "has_70_pairs": size >= 70,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--input-dir", type=Path, default=Path("tools/in"))
    parser.add_argument("--seeds", default="149,150,152,158")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    self_check()
    result = [analyze(args.run, args.input_dir, int(s)) for s in args.seeds.split(",")]
    text = json.dumps({"small_graph_checks": 270, "run_id": args.run.name, "cases": result}, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
