#!/usr/bin/env python3
"""Offline simulation (not a solution): cost of flipping sub-blocks with a "base + flip papers"
layer, compared with complementary blocks (2 papers per block, cost = touched blocks in the wrong
orientation).

Layer: one base paper F (colors Y on all sub-blocks) and k flip papers F_i (colors ~Y on sub-block
S_i only). Sub-block i shows ~Y ("on") iff F_i is above F. A flip paper above F is visible and can be
moved below F (turn off, 1 move); a flip paper below F is hidden, so turning it on needs F to move
below it, which also turns on every flip paper passed on the way.

Each order touches each sub-block with probability q and needs it on or off with probability 1/2.
    bf_sim.py K Q [ORDERS] [POLICY]   POLICY: top (turned-off papers just below F), bottom, or up (the base may also move up)
"""
import random
import sys


def simulate(k, q, orders, policy, seed=1):
    rng = random.Random(seed)
    # stack: list of ids, -1 = F. Top first.
    stack = [-1] + list(range(k))
    moves = 0
    touched_total = 0
    for _ in range(orders):
        need = {}
        for i in range(k):
            if rng.random() < q:
                need[i] = rng.random() < 0.5
        touched_total += len(need)
        if not need:
            continue
        f = stack.index(-1)
        if policy == "up":
            # One base move to the position just below the deepest flip that must be on (or no base
            # move), whichever needs fewer individual turn-offs afterwards.
            need_on = [i for i, v in need.items() if v]
            p_min = max((stack.index(i) for i in need_on), default=-1)  # base goes below this index
            def offs_above(pos):
                return sum(1 for i, v in need.items() if not v and stack.index(i) < pos)
            best = None
            if f > p_min:
                best = (offs_above(f), f)
            cand = p_min + 1 if p_min >= 0 else 0  # base index after the move (in the old stack)
            c = 1 + offs_above(cand)
            if best is None or c < best[0]:
                best = (c, cand)
            if best[1] != f:
                stack.remove(-1)
                pos = best[1] if best[1] < f else best[1] - 1
                stack.insert(pos, -1)
                moves += 1
        else:
            on = set(stack[:f])
            want_on = [i for i, v in need.items() if v and i not in on]
            if want_on:
                deepest = max(stack.index(i) for i in want_on)
                stack.remove(-1)
                stack.insert(deepest, -1)  # just below the deepest needed paper
                moves += 1
        f = stack.index(-1)
        on = set(stack[:f])
        to_off = [i for i, v in need.items() if not v and i in on]
        for i in to_off:
            stack.remove(i)
            f = stack.index(-1)
            if policy in ("top", "up"):
                stack.insert(f + 1, i)
            else:
                stack.append(i)
            moves += 1
    return moves / orders, touched_total / orders


def main():
    k = int(sys.argv[1])
    q = float(sys.argv[2])
    orders = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
    for policy in ("top", "bottom", "up"):
        m, t = simulate(k, q, orders, policy)
        print(f"k={k} q={q} policy={policy}: moves/order {m:.3f}  touched/order {t:.3f}  "
              f"CB moves/order {t / 2:.3f}  ratio {m / (t / 2):.3f}")


if __name__ == "__main__":
    main()
