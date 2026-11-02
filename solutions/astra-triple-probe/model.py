#!/usr/bin/env python3
"""Continuous column-allocation model, not a score prediction or a rigorous lower bound.

The retrieval model extends astra-search4's 0.85 rank-priority mixture to papers
serving 1, 2, or 3 targets. Handle differences are assumed uniform outside the
paper's own (unanimous) handle; target-specific colors/availability and fillers
are not simulated. Compare pairs-only and triple mixtures at the same M/G/map.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def model(h, counts, differences, generic):
    counts = np.asarray(counts, dtype=float)
    active = np.flatnonzero(counts > 0)
    na = len(active)
    q = np.arange(1.0, 4.0)
    col = np.arange(h, dtype=float)
    p = np.asarray(differences) / (h - 1)
    hole = 0.4 * q[None, :] * (h - 1 - col[:, None] + col[:, None] * p[None, :])
    def terms(flat):
        x = np.zeros((h, 3))
        x[:, active] = flat.reshape(h, na)
        n = x.sum(axis=1)
        nt = x @ q
        extra = x[:, 1] + x[:, 2]
        triple = x[:, 2]
        minimum = (n * (n - 1) + extra * (extra - 1) + triple * (triple - 1)) / 2
        uniform = nt * (n - 1) / 2
        retrieval = 0.85 * minimum + 0.15 * uniform
        return x, n, nt, extra, triple, retrieval
    def fun(flat):
        x, _, _, _, _, retrieval = terms(flat)
        return float(retrieval.sum() + (x * hole).sum())
    def jac(flat):
        _, n, nt, extra, triple, _ = terms(flat)
        grad = 0.85 * np.repeat((n - 0.5)[:, None], 3, axis=1)
        grad[:, 1:] += 0.85 * (extra - 0.5)[:, None]
        grad[:, 2] += 0.85 * (triple - 0.5)
        grad += 0.075 * (q[None, :] * (n - 1)[:, None] + nt[:, None])
        return (grad + hole)[:, active].ravel()
    equality = np.tile(np.eye(na), (1, h))
    inequality = np.zeros((h, h * na))
    for c in range(h):
        inequality[c, c * na:c * na + na] = 1
    ans = minimize(fun, np.tile(counts[active] / h, (h, 1)).ravel(), jac=jac,
                   method='SLSQP', bounds=[(0.0, float(counts[j])) for _ in range(h) for j in active],
                   constraints=[{'type': 'eq', 'fun': lambda z: equality @ z - counts[active],
                                 'jac': lambda z: equality},
                                {'type': 'ineq', 'fun': lambda z: inequality @ z - 2,
                                 'jac': lambda z: inequality}],
                   options={'ftol': 1e-8, 'maxiter': 300})
    if not ans.success:
        raise RuntimeError(ans.message)
    x, _, _, _, _, retrieval = terms(ans.x)
    g = float((counts * q * generic).sum()) / 256
    d = float(retrieval.sum()) / 256
    hc = float((x * hole).sum()) / 256
    return {'retrieval': d, 'handle': hc, 'generic': g, 'total_without_lift_return': d + hc + g}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    records = []
    for line in args.input.read_text().splitlines():
        r = json.loads(line)
        if 'pairs_only_count' not in r:
            continue
        h = 64 - r['g']
        pair_n = r['pairs_only_count']
        triple_n = r['greedy_disjoint']
        mix_pair_n = r['mixture_pair_count']
        if pair_n != 64 + r['m'] or mix_pair_n + 2 * triple_n != pair_n:
            r['incomplete_packing'] = True
            records.append(r)
            continue
        r['pairs_model'] = model(h, [256 - 2 * pair_n, pair_n, 0],
                                [0, r['pairs_only_holes'] - r['pairs_only_generic_holes'], 0],
                                [0, r['pairs_only_generic_moves'], 0])
        r['mixed_model'] = model(h, [256 - 2 * mix_pair_n - 3 * triple_n, mix_pair_n, triple_n],
                                [0, r['mixture_pair_holes'] - r['mixture_pair_generic_holes'],
                                 r['selected_mean_holes'] - r['selected_mean_generic_holes']],
                                [0, r['mixture_pair_generic_moves'], r['selected_mean_generic_moves']])
        if not triple_n:
            # The two greedy selections are identical. Reuse the same Monte
            # Carlo generic estimate instead of reporting resampling noise.
            r['mixed_model'] = dict(r['pairs_model'])
        r['model_difference'] = r['mixed_model']['total_without_lift_return'] - r['pairs_model']['total_without_lift_return']
        records.append(r)
    args.output.write_text(''.join(json.dumps(r) + '\n' for r in records))
    for key in sorted({(r['m'], r['g'], r.get('adaptive_steps', 0)) for r in records}):
        rr = [r for r in records if (r['m'], r['g'], r.get('adaptive_steps', 0)) == key and 'model_difference' in r]
        if rr:
            print(key, 'n', len(rr), 'triples', np.mean([r['greedy_disjoint'] for r in rr]),
                  'pairs', np.mean([r['pairs_model']['total_without_lift_return'] for r in rr]),
                  'mixed', np.mean([r['mixed_model']['total_without_lift_return'] for r in rr]),
                  'delta', np.mean([r['model_difference'] for r in rr]))


if __name__ == '__main__':
    main()
