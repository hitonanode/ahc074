"""Behavior-preserving design-only edits, applied to a source argument."""
from pathlib import Path
import argparse

def refactor(s):
    # The integer key is authoritative; the old introduction described a former weight.
    start=s.index('// Objective: the cost of the pairs of targets')
    end=s.index('struct WindowStats',start)
    s=s[:start]+'''// Objective: a greedy matching of 71 compatible close pairs (distance <= 26),
// priced by 0.5 handle differences + both targets' mean generic moves + 0.04 differences.
// The mean pair cost has a penalty of 10 per missing pair. Integer keys in 1/3600
// (1800 hd + 5 PosetSums::both_of + 144 d) have stable ties by pair index.
// Moves change window roles, sheet pairs or polarity; evaluate_pairs updates the
// affected relations before the exact matching. A rejected move restores mask/pol.
'''+s[end:]
    s=s.replace('the ascending order of the entries is the stable order by key of climb4-fast (ties in the order\n',
                'the ascending order of the entries is stable by key (ties in the order\n')
    s=s.replace('            // hd <= 26, full144 <= 144*26, and the six-sheet table\'s rel <= 4380.',
                '            // hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.')
    undo='''    auto undo_move = [&](const Move& mv) {
        mask[mv.ea] = mv.olda;
        mask[mv.eb] = mv.oldb;
        pol = mv.oldpol;
    };
'''
    assert s.count(undo)==1
    s=s.replace(undo,'')
    pos=s.index('    // A swap deletes window a and adds window b.')
    s=s[:pos]+undo+s[pos:]
    for old in [
        '            mask[ea] = olda;\n            mask[eb] = oldb;\n            pol = oldpol;',
        '                mask[ea] = olda; mask[eb] = oldb; pol = oldpol;',
        '                    mask[ea] = olda;\n                    mask[eb] = oldb;\n                    pol = oldpol;']:
        assert old in s
        indent=old[:len(old)-len(old.lstrip())]
        s=s.replace(old,indent+'undo_move(mv);')

    # Both search phases propose and screen the same way. Only acceptance differs.
    first=s.index('        const bool path_move = path_active && propose_elite(mv);')
    last=s.index('        const bool force = it - last_accept_it >= kMapStall',first)
    old=s[first:last]
    new='''        double candidate;
        if (!propose_candidate(it, kMapStall, candidate)) continue;
        auto temp = [&] { return 0.05 * std::pow(0.00125 / 0.05, progress); };
'''
    s=s[:first]+new+s[last:]
    first=s.index('            const bool path_move = path_active && propose_elite(mv);')
    last=s.index('            const bool force = it - last_accept_it >= kClimbStall',first)
    s=s[:first]+'''            double candidate;
            if (!propose_candidate(it, kClimbStall, candidate)) continue;
'''+s[last:]
    pos=s.index('#if DESIGN_PROFILE\n    unsigned long long dp_loop_start')
    s=s[:pos]+'''    // Both phases share proposal, cache lookup and tabu filtering. A new best
    // overrides tabu; otherwise rejected proposals leave mask/pol unchanged.
    auto propose_candidate = [&](int it, int stall, double& candidate) {
        const bool path_move = path_active && propose_elite(mv);
        if (!path_move && it - last_accept_it >= stall && escape_valid) {
            if (!propose_elite(mv)) install_escape();
        } else if (!path_move) {
            DP_SCOPE(aw_propose);
            if (!propose(mv)) return false;
        }
        candidate = candidate_cost();
        if (tabu_epoch[move_key] > epoch && candidate >= best - 1e-9) {
            ++tabu_skips;
            undo_move(mv);
            return false;
        }
        remember_escape(candidate);
        return true;
    };
'''+s[pos:]

    # Swap the handle coordinate in one place; column membership is a separate edit.
    swap='''            std::swap(D.handle[a], D.handle[b]);
            for (auto& h : D.hb) {
                const u64 t = ((h >> a) ^ (h >> b)) & 1;
                h ^= (t << a) | (t << b);
            }
            for (auto& row : rows) {
                std::swap(row.t1[a], row.t1[b]);
                std::swap(row.u1[a], row.u1[b]);
                std::swap(row.p1[a], row.p1[b]);
                std::swap(row.pd[a], row.pd[b]);
            }
'''
    s=s.replace('''            // bits a and b of every target exchanged, without branches (vectorized; a branch per
            // target would be mispredicted half of the time)
''','')
    assert s.count(swap)==2
    s=s.replace(swap,'            swap_handle_windows(a, b);\n')
    pos=s.index('        // Exchange the handles at positions a < b.')
    helper='''        // Rename two handle coordinates in every target and aggregate row.
        // Column membership and cached costs are updated by the caller.
        void swap_handle_windows(int a, int b) {
'''+swap+'''        }
'''
    s=s[:pos]+helper+s[pos:]

    # Same formula, same operation order: model / heads / perforation share it.
    pos=s.index('    double hcost(int j) const {')
    end=s.index('    // The reset demand',pos)
    s=s[:pos]+'''    static double hole_cost_of(double x, double y, double reset) {
        return 4 * kHoleWeight * (x * y + .5 * reset * std::min(x, y)) / std::max(1., x + y + reset);
    }
    static std::array<double, 2> head_probability(double x, double y, double reset) {
        const double n = x + y + reset, p = n ? (y + reset * (y > x)) / n : .5;
        return {1 - p, p};
    }
    double hcost(int j) const { return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]); }
'''+s[end:]
    old='''        for (int c = 0; c < H; c++) {
            double x = hn[c][0], y = hn[c][1], t = 2.0 * nt[c], n = x + y + t;
            double p = n ? (y + t * (y > x)) / n : .5;
            color_probability[c] = {1 - p, p};
        }'''
    assert old in s
    s=s.replace(old,'''        for (int c = 0; c < H; c++)
            color_probability[c] = head_probability(hn[c][0], hn[c][1], 2.0 * nt[c]);''')
    old='''        for (int c = 0; c < d.H; c++) {
            double x = d.hn[c][0], y = d.hn[c][1], t = strength * d.nt[c], n = x + y + t,
                   p = n ? (y + t * (y > x)) / n : .5;
            prob[c] = {1 - p, p};
        }'''
    assert old in s
    s=s.replace(old,'''        for (int c = 0; c < d.H; c++)
            prob[c] = Design::head_probability(d.hn[c][0], d.hn[c][1], strength * d.nt[c]);''')
    s=s.replace('''        double x = counts[c][0], y = counts[c][1], r = 2 * demands[c];
        return 4 * Design::kHoleWeight * (x * y + .5 * r * std::min(x, y)) / std::max(1., x + y + r);''',
    '''        return Design::hole_cost_of(counts[c][0], counts[c][1], 2 * demands[c]);''')
    s=s.replace('''            double x = counts[c][0], y = counts[c][1], r = 2 * demands[c], n = x + y + r;
            double p = n ? (y + r * (y > x)) / n : .5;
            probability[c] = {1 - p, p};''',
    '''            probability[c] = Design::head_probability(counts[c][0], counts[c][1], 2 * demands[c]);''')
    s=s.replace('''        update_probability();
        rebuild();
    }
    void update_probability()''','''        rebuild();  // Includes update_probability().
    }
    void update_probability()''')

    # Share the independent-error recurrence while retaining its summation order.
    pos=s.index('    // The expected saving of the paper of a unit')
    helper='''    // Expected fixes saved minus placement/return cost; probability(j) gives
    // the chance that covered handle j is wrong. Keep increasing-bit order.
    template<class Probability>
    static double covered_gain(u64 covered, Probability probability) {
        if (!covered) return 0;
        double p0 = 1, p1 = 0, expected = 0;
        for (u64 z = covered; z; z &= z - 1) {
            const double p = probability(__builtin_ctzll(z));
            expected += p;
            p1 = p1 * (1 - p) + p0 * p;
            p0 *= 1 - p;
        }
        return std::max(0.0, expected - (1 - p0) - 0.6 * (1 - p0 - p1));
    }
'''
    s=s[:pos]+helper+s[pos:]
    pos=s.index('        if (!covered) return 0;  // The empty recurrence returns exactly +0.')
    end=s.index('\n    }',pos)
    s=s[:pos]+'''        return covered_gain(covered, [&](int j) { return 0.5 * (q[j + 1] - q[j]); });'''+s[end:]
    pos=s.index('        if (!cover) return 0;  // Empty recurrence: exactly +0.')
    end=s.index('\n    }',pos)
    s=s[:pos]+'''        return Design::covered_gain(cover, [&](int j) { return bad[u][j]; });'''+s[end:]

    # The scalar DP used for a changed donor's own targets is the cache's forward pass.
    start=s.index('    double solve_edges(const Edges& edges) const {')
    end=s.index('        for (int lo = H - 1;',start)
    s=s[:start]+'''    std::array<double, 65> forward_values(const Edges& edges) const {
        std::array<double, 65> dp{};
        for (int c = 0; c < H; c++) {
            dp[c + 1] = dp[c];
            for (u64 z = edges.starts[c]; z; z &= z - 1) {
                const int lo = __builtin_ctzll(z);
                dp[c + 1] = std::max(dp[c + 1], dp[lo] + edges[c][lo]);
            }
        }
        return dp;
    }
    double solve_edges(const Edges& edges) const { return forward_values(edges)[H]; }
    QueryCache make_cache(const Edges& edges) const {
        QueryCache q;
        q.forward = forward_values(edges);
        q.value = q.forward[H];
'''+s[end:]
    # Comments describe current invariants, not the discarded implementation.
    s=s.replace('''// comparison: every query is the closure of an acyclic relation, a key of the table. (climb4-fast: 2^18
// 64-bit keys and two arrays of the sums, 3 MB, two cache lines and a probe loop per lookup.) The values
// are the same sums of the same classes (checked over all 130023 relations with -DPOSET_VERIFY).''',
    '''// comparison: every query is an acyclic closure, hence a key of the table.
// POSET_VERIFY checks the sums over all 130023 relations.''')
    start=s.index('    // The state of the annealing, NR registers')
    end=s.index('#define ANNEAL_TARGET',start)
    s=s[:start]+'''    // NR AVX2 registers cover H <= 8*NR handles. Evaluate without mutation;
    // commit the hole counts and qf values only after acceptance.
    // rows[c].t1/u1/p1/pd count targets/units/pairs of color 1 and differing pairs
    // at every handle. Handle exchanges use these column aggregates.
    // key[x] = 2*column + handle color identifies partners for two-unit moves.
'''+s[end:]
    s=s.replace('    // for all 70 matching pairs into two words, then count swap losses with two popcounts.',
                '    // for the selected pairs into two words, then count swap losses with two popcounts.')
    # Make the long assignment stage navigable; the merger owns the header TOC.
    for needle,title in [
        ('    // A move: its windows and sheet pairs;', 'Window assignment: candidate screens and tables'),
        ('    auto propose =', 'Window assignment: ordinary moves'),
        ('    struct Elite {', 'Window assignment: elite paths'),
        ('    auto apply_move =', 'Window assignment: acceptance and search loops'),
        ('        // p0, p1: the slice of the whole schedule', 'Design annealing: move proposals')]:
        pos=s.index(needle)
        indent=needle[:len(needle)-len(needle.lstrip())]
        s=s[:pos]+indent+'// ==== '+title+' ====\n\n'+s[pos:]
    return s

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
    Path(a.output).write_text(refactor(Path(a.source).read_text()))
