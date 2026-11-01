#!/usr/bin/env python3
"""採用ソースの目的値キャッシュと最終状態を再計算する診断用コピーを作る。"""
from pathlib import Path
import hashlib,json,sys
h=Path(__file__).resolve().parent
source=sys.argv[1] if len(sys.argv)>1 else 'main'
s=(h/(source+'.cpp')).read_text()
base=(h.parent/'imp-s2hd/main.cpp').read_text()
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
# For the optional transfer sampler, compare every direction with full reconstruction.
if 'make_transfer_options' in s:
    s=s.replace('    auto make_transfer_options =', '    long long checked_options = 0;\n    auto make_transfer_options =')
    needle='        return (~four & ((1U << 30) - 1)) & ~((1U << ea) | (1U << (ea + 15)));'
    assert s.count(needle)==1
    s=s.replace(needle,r'''        const uint32_t options = (~four & ((1U << 30) - 1)) & ~((1U << ea) | (1U << (ea + 15)));
        if ((transfer_rows & 127) == 0) {
            const u64 oldpol = pol, olda = mask[ea];
            for (int code = 0; code < 30; ++code) {
                const int eb = code % 15;
                if (ea == eb) { assert(!(options >> code & 1)); continue; }
                const u64 oldb = mask[eb];
                mask[ea] &= ~(1ULL << a); mask[eb] |= 1ULL << a;
                pol = (pol & ~(1ULL << a)) | (u64(code / 15) << a);
                int losses = 0;
                for (int p : selected) {
                    uint32_t r; int rel;
                    pair_state(pairs.au[p], pairs.diff[p], r, rel);
                    losses += !rel;
                }
                mask[ea] = olda; mask[eb] = oldb; pol = oldpol;
                assert(bool(options >> code & 1) == (losses < kRejectLoss));
                ++checked_options;
            }
        }
        return options;''')
    s=s.replace('    stats.gobj_after = cur;', r'''    std::cerr << "checked_options = " << checked_options << '\n';
    stats.gobj_after = cur;''')
    if 'priority_values' in s:
        s=s.replace('long long checked_options = 0;', 'long long checked_options = 0, checked_priority = 0;')
        s=s.replace('            const u64 oldpol = pol, olda = mask[ea];', r'''            const u64 oldpol = pol, olda = mask[ea];
            std::vector<int> before(selected.size());
            mask[ea] &= ~(1ULL << a);
            for (int i = 0; i < int(selected.size()); ++i) {
                const int p = selected[i];
                uint32_t r;
                pair_state(pairs.au[p], pairs.diff[p], r, before[i]);
            }
            mask[ea] = olda;''')
        s=s.replace('                int losses = 0;', '                int losses = 0, expected = 0, index = 0;')
        s=s.replace('                    losses += !rel;', r'''                    losses += !rel;
                    expected += rel ? rel - before[index] : 0;
                    ++index;''')
        s=s.replace('                ++checked_options;', r'''                assert(added_cost[code] == expected);
                ++checked_priority;
                ++checked_options;''')
        s=s.replace('    stats.gobj_after = cur;', r'''    std::cerr << "checked_priority = " << checked_priority << '\n';
    stats.gobj_after = cur;''')
(h/'verify-check.cpp').write_text(s)
print(scope)
