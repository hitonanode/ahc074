#!/usr/bin/env python3
"""Chapter 5 feasibility: incompatible near pairs, repair candidates and their access under the SOTA's
request policy, from the saved outputs of a recorded run (no solver is run).

usage: analyze.py --run RUN --seeds A-B [--dist 26] [--emax 3] [--out FILE.json] [--validate N]

Per seed (all numbers per case, output paper numbering):
  * the comparator: the 6 generic sheets (role "generic"), G = their opaque windows, the 720 orders;
  * near pairs (Hamming distance <= dist over the 64 windows) and, per side x of a pair, err_x = the least
    number of differing generic windows that every order of the 6 sheets shows wrongly for x;
  * repair candidates of a side: a paper R (not the cap, a generic sheet or either product's paper)
    inserted at some depth p of the generic layer under some order sigma makes the display right on all
    differing generic windows, and R's colors are right on the differing non-generic windows (where the
    shared paper has holes). Deeper handles of the shared paper are assumed covered (optimistic);
  * replay of the saved moves (visibility checked) with the move labels (@ops): what each request moves,
    which papers are visible at its start, and for every request of a side that needs a repair, the
    access of each candidate at the start of that request: moved anyway by the SOTA's plan (and by which
    label), visible, or the exposure cost (the papers above it on its least covered window).
"""
import argparse
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from numba import njit

sys.path.insert(0, '/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/scripts')
import replay  # noqa: E402

FULL = (1 << 64) - 1


def popcount(x):
    return bin(x).count('1')


def to_u64(x):
    return np.uint64(x & FULL)


@njit(cache=True)
def pc64(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return int((x * np.uint64(0x0101010101010101)) >> np.uint64(56))


@njit(cache=True)
def side_err(disp, t, dg):
    """least number of windows of dg where an order's display differs from t, and the count of orders
    reaching it"""
    best = 99
    for i in range(disp.shape[0]):
        e = pc64((disp[i] ^ t) & dg)
        if e < best:
            best = e
    return best


@njit(cache=True)
def candidates_of(ad, ac, bd, pb, po, t, dg, dn, exclude):
    """papers R with some (order, depth) making the display right on dg (target t) and R right on its
    opaque windows of dn. ad/ac: display/cover of the sheets above depth p; bd: display of the sheets
    below (with its own cover); pb/po: black/opaque of all papers."""
    out = []
    n = ad.shape[0]
    for r in range(pb.shape[0]):
        if exclude[r]:
            continue
        o, b = po[r], pb[r]
        if (b ^ t) & o & dn:
            continue
        ok = False
        for i in range(n):
            d = ad[i] | (b & ~ac[i]) | (bd[i] & ~(ac[i] | o))
            if ((d ^ t) & dg) == 0:
                ok = True
                break
        if ok:
            out.append(r)
    return out


@njit(cache=True)
def print_changes(ad, ac, bd, pb, po, t, dg, dn, exclude):
    """for every paper R: the fewest generic windows to make holes in R (and those windows as a mask) so
    that R inserted at some (order, depth) gives the right display on dg, where a hole shows the sheets
    below; -1 if no (order, depth) works or R is wrong on its opaque windows of dn"""
    m = pb.shape[0]
    best = np.full(m, -1, np.int64)
    holes = np.zeros(m, np.uint64)
    for r in range(m):
        if exclude[r]:
            continue
        o, b = po[r], pb[r]
        if (b ^ t) & o & dn:
            continue
        bh = 99
        bm = np.uint64(0)
        for i in range(ad.shape[0]):
            vis = o & ~ac[i] & dg
            right = vis & ~(b ^ t)
            # the windows R does not show rightly must be shown rightly by the sheets (above or below)
            rest = dg & ~right
            d = ad[i] | (bd[i] & ~ac[i])
            if ((d ^ t) & rest) != 0:
                continue
            h = vis & (b ^ t)
            c = pc64(h)
            if c < bh:
                bh = c
                bm = h
        if bh < 99:
            best[r] = bh
            holes[r] = bm
    return best, holes


@njit(cache=True)
def exposure_costs(order, po, k):
    """exposure cost of every paper at this stack (top first): the least, over its opaque windows, number
    of papers above it opaque there (0: visible)"""
    cnt = np.zeros(64, np.int64)
    exp = np.zeros(k, np.int64)
    for i in range(order.shape[0]):
        x = order[i]
        o = po[x]
        best = 1 << 30
        for w in range(64):
            if (o >> np.uint64(w)) & np.uint64(1):
                if cnt[w] < best:
                    best = cnt[w]
        exp[x] = best if best < (1 << 30) else 1 << 20
        for w in range(64):
            if (o >> np.uint64(w)) & np.uint64(1):
                cnt[w] += 1
    return exp


def comparator_tables(papers, generic):
    """per (order of the generic sheets, insertion depth p in 0..6): display and cover above p, display
    below p (with its own cover), and the full display of each order"""
    ad, ac, bd = [], [], []
    full = []
    for perm in itertools.permutations(generic):
        for p in range(7):
            a_d = a_c = 0
            for s in perm[:p]:
                a_d |= papers[s].black & ~a_c
                a_c |= papers[s].opaque
            b_d = b_c = 0
            for s in perm[p:]:
                b_d |= papers[s].black & ~b_c
                b_c |= papers[s].opaque
            ad.append(a_d)
            ac.append(a_c)
            bd.append(b_d)
        d = c = 0
        for s in perm:
            d |= papers[s].black & ~c
            c |= papers[s].opaque
        full.append(d)
    arr = lambda v: np.array([to_u64(x) for x in v], dtype=np.uint64)
    return arr(ad), arr(ac), arr(bd), arr(full)


def analyze_seed(run_dir, seed, dist, emax, validate):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (run_dir / 'out' / f'{seed:04d}.txt').read_text())
    err_text = (run_dir / 'err' / f'{seed:04d}.txt').read_text()
    ann = replay.parse_annotations(err_text, inp.k)
    role = ann.papers['role']
    targets = ann.papers['targets']
    papers = out.designs
    K = inp.k
    generic = [k for k in range(K) if role[k] == 'generic']
    cap = [k for k in range(K) if role[k] == 'cap']
    assert len(generic) == 6, generic
    G = 0
    for s in generic:
        G |= papers[s].opaque
    paper_of = {}
    for k in range(K):
        if targets[k] != '-':
            for t in targets[k].split(','):
                paper_of[int(t)] = k
    A = inp.target
    P = inp.p
    ad, ac, bd, full = comparator_tables(papers, generic)
    pb = np.array([to_u64(p.black) for p in papers], dtype=np.uint64)
    po = np.array([to_u64(p.opaque) for p in papers], dtype=np.uint64)
    res = {'seed': seed, 'G': popcount(G)}
    # ---- near pairs
    hist = Counter()
    sides = []  # (pair index, x, partner, err, candidates)
    codesign = []  # 1-window sides: (pair index, x, [(repair paper, holes added)])
    pairs = []
    for u in range(P):
        for v in range(u + 1, P):
            delta = A[u] ^ A[v]
            if popcount(delta) > dist:
                continue
            dg = delta & G
            dn = delta & ~G
            eu = side_err(full, to_u64(A[u] & dg), to_u64(dg))
            ev = side_err(full, to_u64(A[v] & dg), to_u64(dg))
            hist[(min(eu, 9), min(ev, 9))] += 1
            if (eu == 0 and ev == 0) or max(eu, ev) > emax:
                continue
            idx = len(pairs)
            pairs.append((u, v, eu, ev, popcount(dg)))
            for x, y, e in ((u, v, eu), (v, u, ev)):
                if e == 0:
                    continue
                excl = np.zeros(K, np.bool_)
                for k in generic + cap + [paper_of.get(u, -1), paper_of.get(v, -1)]:
                    if k >= 0:
                        excl[k] = True
                cands = list(candidates_of(ad, ac, bd, pb, po, to_u64(A[x] & dg), to_u64(dg), to_u64(dn), excl))
                sides.append((idx, x, y, e, cands))
                if e == 1:
                    nh, hm = print_changes(ad, ac, bd, pb, po, to_u64(A[x] & dg), to_u64(dg), to_u64(dn), excl)
                    # co-designable repair papers: holes added only on generic windows, and the repair
                    # paper's own targets still displayable by the comparator with those holes
                    ok = []
                    for R in range(K):
                        if nh[R] < 0:
                            continue
                        hmask = int(hm[R])
                        own = [int(z) for z in targets[R].split(',')] if targets[R] != '-' else []
                        own_delta = (A[own[0]] ^ A[own[1]]) if len(own) == 2 else 0
                        dg2 = (own_delta | hmask) & G
                        if all(side_err(full, to_u64(A[z] & dg2), to_u64(dg2)) == 0 for z in own):
                            ok.append((R, int(nh[R])))
                    codesign.append((idx, x, ok))
    res['near_hist'] = {f'{a},{b}': c for (a, b), c in sorted(hist.items())}
    res['near_pairs'] = sum(hist.values())
    res['compatible'] = hist[(0, 0)]
    # rescuable pairs: every side needing a repair has a candidate
    side_by_pair = defaultdict(list)
    for s in sides:
        side_by_pair[s[0]].append(s)
    rescuable = [i for i, (u, v, eu, ev, _) in enumerate(pairs)
                 if all(len(s[4]) > 0 for s in side_by_pair[i])]
    res['incompatible_pairs_emax'] = len(pairs)
    res['by_err'] = dict(Counter(f'{min(p[2], p[3])}-{max(p[2], p[3])}' for p in pairs))
    res['rescuable'] = len(rescuable)
    res['rescuable_by_err'] = dict(Counter(f'{min(pairs[i][2], pairs[i][3])}-{max(pairs[i][2], pairs[i][3])}' for i in rescuable))
    res['cands_per_side'] = [len(s[4]) for s in sides if s[0] in set(rescuable)]
    # print co-design (1-window pairs): sides with a repair paper whose own targets stay displayable after
    # the added holes; pairs with such papers for both sides (distinct papers), by the holes added
    cd = defaultdict(dict)
    for idx, x, ok in codesign:
        cd[idx][x] = ok
    for hmax in (0, 1, 2, 3, 99):
        n_side = sum(1 for idx, x, ok in codesign if any(h <= hmax for _, h in ok))
        n_pair = 0
        for idx, d in cd.items():
            if len(d) != 2:
                continue
            (x1, ok1), (x2, ok2) = d.items()
            a1 = {R for R, h in ok1 if h <= hmax}
            a2 = {R for R, h in ok2 if h <= hmax}
            if a1 and a2 and (len(a1 | a2) >= 2):
                n_pair += 1
        res[f'codesign_sides_h{hmax}'] = n_side
        res[f'codesign_pairs_h{hmax}'] = n_pair
    res['onewindow_sides'] = len(codesign)
    # ---- replay with labels
    game = replay.Game(inp, papers)
    need = defaultdict(list)  # product x -> rescuable sides of x
    for s in sides:
        if s[0] in set(rescuable):
            need[s[1]].append(s)
    label_count = Counter()
    moved_per_request = []
    visible_at_start = []
    prev_paper = -1
    prev_fate = Counter()
    uses = []  # per (request, side): min costs
    moved_by_product = defaultdict(list)  # product -> list of {paper: label} of its requests
    val_checked = val_legal = 0
    order_arr = np.zeros(K, np.int64)
    for r, ops in enumerate(out.queries):
        labels = ann.labels_of(r, len(ops))
        x = inp.requests[r]
        order_arr[:] = game.order
        start_order = list(game.order)
        exp = exposure_costs(order_arr, po, K)
        vis = sum(1 for k in range(K) if exp[k] == 0)
        visible_at_start.append(vis)
        moved = {}
        for (k, d), lab in zip(ops, labels):
            moved.setdefault(k, lab)
            label_count[lab] += 1
        moved_per_request.append(len(moved))
        moved_by_product[x].append(moved)
        if prev_paper >= 0:
            prev_fate[moved.get(prev_paper, 'kept')] += 1
        for s in need.get(x, []):
            best_opt = best_real = math.inf
            how = 'none'
            for R in s[4]:
                if R in moved:
                    c_opt, c_real, h = 0.0, 0.96, 'moved:' + moved[R]
                elif exp[R] == 0:
                    c_opt, c_real, h = 1.0, 1.96, 'visible'
                else:
                    c_opt, c_real, h = 1.0 + exp[R], 1.96 + exp[R], f'exp{min(exp[R], 9)}'
                if R == prev_paper:
                    h += '+prev'
                if c_opt < best_opt or (c_opt == best_opt and c_real < best_real):
                    best_opt, best_real, how = c_opt, c_real, h
            uses.append({'pair': s[0], 'x': x, 'opt': best_opt, 'real': best_real, 'how': how})
            # legal check of the exposure: move the covering papers of the cheapest unmoved candidate
            # (top first, to the bottom), then the candidate itself to the top, visibility checked
            if validate and val_checked < validate and how.startswith('exp'):
                R = min((c for c in s[4] if c not in moved), key=lambda c: exp[c])
                g2 = replay.Game(inp, papers)
                g2.order = list(start_order)
                o = papers[R].opaque
                pos = g2.order.index(R)
                best_w = min((w for w in range(64) if o >> w & 1),
                             key=lambda w: sum(1 for y in g2.order[:pos] if papers[y].opaque >> w & 1))
                cover = [y for y in g2.order[:pos] if papers[y].opaque >> best_w & 1]
                try:
                    for y in cover:
                        g2.move(y, K - 1)
                    g2.move(R, 0)
                    val_legal += 1
                except replay.InvalidMove:
                    pass
                val_checked += 1
        for k, d in ops:
            game.move(k, d)
        game.finish(r)
        prev_paper = paper_of.get(x, -1)
    res['label_per_request'] = {k: v / len(out.queries) for k, v in sorted(label_count.items())}
    res['moved_papers_per_request'] = float(np.mean(moved_per_request))
    res['visible_at_start'] = float(np.mean(visible_at_start))
    res['prev_fate'] = dict(prev_fate)
    res['uses'] = uses
    # the paper (other than the cap, the generic sheets and x's own paper) moved in the largest share of
    # the requests of x, its share and labels; over the products with at least 3 requests
    reliable = []
    gen_set = set(generic + cap)
    for x, lst in moved_by_product.items():
        if len(lst) < 3:
            continue
        own = paper_of.get(x, -1)
        cnt = Counter()
        labs = defaultdict(Counter)
        for m in lst:
            for k, lab in m.items():
                if k in gen_set or k == own:
                    continue
                cnt[k] += 1
                labs[k][lab] += 1
        if cnt:
            k, c = cnt.most_common(1)[0]
            reliable.append({'x': x, 'n': len(lst), 'share': c / len(lst), 'paper': k,
                             'labels': dict(labs[k]), 'same_col': ann.papers['col'][k] == ann.papers['col'][own] if own >= 0 else False})
        else:
            reliable.append({'x': x, 'n': len(lst), 'share': 0.0, 'paper': -1, 'labels': {}, 'same_col': False})
    res['reliable'] = reliable
    res['validate'] = [val_checked, val_legal]
    res['score_check'] = game.score()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default='20261108-063038_legal-tie-fix')
    ap.add_argument('--seeds', default='0-20')
    ap.add_argument('--dist', type=int, default=26)
    ap.add_argument('--emax', type=int, default=3)
    ap.add_argument('--validate', type=int, default=50)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split('-'))
    run_dir = replay.resolve_run(a.run)
    results = []
    for seed in range(lo, hi):
        r = analyze_seed(run_dir, seed, a.dist, a.emax, a.validate)
        results.append(r)
        print(f'seed {seed}: near {r["near_pairs"]} compatible {r["compatible"]} incompatible(<= {a.emax}) '
              f'{r["incompatible_pairs_emax"]} rescuable {r["rescuable"]} uses {len(r["uses"])} '
              f'validate {r["validate"]} score {r["score_check"]}', flush=True)
    if a.out:
        Path(a.out).write_text(json.dumps(results))


if __name__ == '__main__':
    main()
