#!/usr/bin/env python3
"""採用ソースの目的値キャッシュと最終状態を再計算する診断用コピーを作る。"""
from pathlib import Path
import hashlib,json
h=Path(__file__).resolve().parent
s=(h/'main.cpp').read_text()
base=(h.parent/'astra-search/main.cpp').read_text()
begin='WindowStats assign_windows('
end='// kBitLanes[v][i]'
a,b=s.index(begin),s.index(end)
ba,bb=base.index(begin),base.index(end)
mc0=s.index('    auto matching_cost =')
mc1=s.index('    // A move:',mc0)
bmc0=base.index('    auto matching_cost =')
bmc1=base.index('    // A move:',bmc0)
scope={'before_assign_identical':s[:a]==base[:ba], 'after_assign_identical':s[b:]==base[bb:], 'matching_cost_identical':s[mc0:mc1]==base[bmc0:bmc1], 'main_sha256':hashlib.sha256(s.encode()).hexdigest()}
assert all(scope[k] for k in ['before_assign_identical','after_assign_identical','matching_cost_identical'])
(h/'scope-summary.json').write_text(json.dumps(scope,indent=2)+'\n')
# Re-evaluate sampled exact-cache hits. No RNG calls; fixed-iteration trajectories must agree.
s=s.replace('    auto handles_after =',r'''
    long long checked_memo = 0, checked_states = 0;
    auto check_memo = [&](const Move& mv, double expected) {
        if (!memo_hit || (memo_hits & 127)) return;
        int ea = mv.ea, eb = mv.eb;
        if (ea == eb)
            nvalid = evaluate_move<false>(pairs, relations, pol, fwd[ea] | rev[ea], mask[ea], mask[ea],
                                         fwd[ea], fwd[ea], ndir.data(), nrel.data(), valid.data(), pending.data());
        else
            nvalid = evaluate_move<true>(pairs, relations, pol, fwd[ea] | rev[ea] | fwd[eb] | rev[eb], mask[ea], mask[eb],
                                        fwd[ea], fwd[eb], ndir.data(), nrel.data(), valid.data(), pending.data());
        double actual = matching_cost(nrel.data(), hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0));
        assert(std::abs(expected-actual)<1e-10);
        ++checked_memo;
    };
    auto handles_after =''')
s=s.replace('memo_value[move_key] = candidate;', 'memo_value[move_key] = candidate;\n        check_memo(mv, candidate);')
needle='    stats.gobj_after = cur;'
assert s.count(needle)==1
s=s.replace(needle,r'''
    // Rebuild every relation and the exact greedy matching from the returned assignment.
    hm = ~0ULL;
    for (u64 x : mask) hm &= ~x;
    nvalid = 0;
    for (int p = 0; p < np; ++p) {
        pair_state(pairs.au[p], pairs.diff[p], pairs.dir[p], pairs.rel[p]);
        if (pairs.rel[p]) valid[nvalid++] = p;
        ++checked_states;
    }
    const double rebuilt = matching_cost(pairs.rel.data(), hm);
    assert(std::abs(cur-rebuilt)<1e-10);
    std::cerr << "checked_memo = " << checked_memo << "\nchecked_states = " << checked_states << '\n';
    stats.gobj_after = cur;''')
(h/'verify-check.cpp').write_text(s)
print(scope)
