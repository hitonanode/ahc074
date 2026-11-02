#!/usr/bin/env python3
"""診断用コピーだけに再計算の照合を入れる。提出ソースは変更しない。"""
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('target',default='main',nargs='?');a=p.parse_args()
here=Path(__file__).resolve().parent
s=(here/(a.target+'.cpp')).read_text()
s=s.replace('    long long screen_rejected =', '    long long verify_swaps = 0, verify_transfers = 0, verify_states = 0;\n    long long screen_rejected =',1)
start=s.index('    auto swap_losses =')
end=s.index('    // Cache exact objective values',start)
part=s[start:end]
part=part.replace('        return lost;', '''        if ((screen_checks & 255) == 0) {
            const u64 saved_mask = mask[mv.ea];
            mask[mv.ea] = (mv.olda & ~(1ULL << mv.a)) | (1ULL << mv.b);
            int exact = 0;
            for (int p : selected) {
                uint32_t r; int cost;
                pair_state(pairs.au[p], pairs.diff[p], r, cost);
                exact += cost == 0;
            }
            assert(lost == exact);
            mask[mv.ea] = saved_mask;
            ++verify_swaps;
        }
        return lost;''')
s=s[:start]+part+s[end:]
needle='                    transfer_options[a] = make_transfer_options(a, ea);'
check='''
                    if ((transfer_rows & 63) == 0) {
                        const u64 saved_mask = mask[ea], saved_pol = pol;
                        mask[ea] &= ~(1ULL << a);
                        std::vector<int> before;
                        for (int p : selected) {
                            uint32_t r; int cost;
                            pair_state(pairs.au[p], pairs.diff[p], r, cost);
                            assert(cost > 0); before.push_back(cost);
                        }
                        for (int code = 0; code < 30; ++code) {
                            const int e = code % 15;
                            if (e == ea) continue;
                            const u64 saved_other = mask[e];
                            mask[e] |= 1ULL << a;
                            pol = (saved_pol & ~(1ULL << a)) | (u64(code/15) << a);
                            int lost = 0, delta = 0, i = 0;
                            for (int p : selected) {
                                uint32_t r; int cost;
                                pair_state(pairs.au[p], pairs.diff[p], r, cost);
                                lost += cost == 0;
                                if (cost) delta += cost - before[i];
                                ++i;
                            }
                            const bool available = (transfer_options[a] >> code) & 1;
                            assert(available == (lost < kRejectLoss));
                            if (available && __builtin_popcount(transfer_options[a]) > 1)
                                assert(transfer_priority[a][code] == delta);
                            ++verify_transfers;
                            mask[e] = saved_other;
                        }
                        mask[ea] = saved_mask; pol = saved_pol;
                    }
'''
assert needle in s;s=s.replace(needle,needle+check,1)
needle='    stats.gobj_after = cur;'
check='''    {
        u64 generic = 0;
        for (u64 windows : mask) { assert(windows); assert(!(generic & windows)); generic |= windows; }
        assert(__builtin_popcountll(generic) == g);
        u64 seen = 0;
        for (int j = 0; j < 64; ++j) {
            assert(!(seen >> order[j] & 1)); seen |= 1ULL << order[j];
            assert(bool(generic >> order[j] & 1) == (j < g));
        }
        nvalid = 0;
        for (int p = 0; p < np; ++p) {
            pair_state(pairs.au[p], pairs.diff[p], ndir[p], nrel[p]);
            if (nrel[p]) valid[nvalid++] = p;
            ++verify_states;
        }
        const double rebuilt = matching_cost(nrel.data(), ~generic);
        assert(std::abs(rebuilt - cur) < 1e-9);
    }
    std::cerr << "verify_swaps = " << verify_swaps << "\\nverify_transfers = " << verify_transfers
              << "\\nverify_states = " << verify_states << '\\n';
'''
assert needle in s;s=s.replace(needle,check+needle,1)

needle='                    window_options[a] = prepare_windows(a, ea);'
check=r'''
                    if ((window_rows & 511) == 0) {
                        const u64 saved_mask = mask[ea], saved_pol = pol;
                        for (u64 q = hm; q; q &= q-1) {
                            const int b = __builtin_ctzll(q);
                            mask[ea] = (saved_mask & ~(1ULL << a)) | (1ULL << b);
                            for (int color = 0; color < 2; ++color) {
                                pol = (saved_pol & ~(1ULL << b)) | (u64(color) << b);
                                int lost = 0;
                                for (int p : selected) {
                                    uint32_t r; int cost;
                                    pair_state(pairs.au[p], pairs.diff[p], r, cost);
                                    lost += cost == 0;
                                }
                                assert(bool(window_options[a][color] >> b & 1) == (lost < kRejectLoss));
                                ++verify_windows;
                            }
                        }
                        mask[ea] = saved_mask; pol = saved_pol;
                    }
'''
if needle in s:
    s=s.replace(needle,needle+check,1)
    s=s.replace('long long verify_swaps = 0,', 'long long verify_windows = 0, verify_swaps = 0,',1)
    s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "verify_windows = " << verify_windows << \'\\n\';\n    stats.gobj_after = cur;',1)

(here/'verify-check.cpp').write_text(s)

# The new cross moves are checked against all constraints in sampled rows.
s=s.replace('long long verify_windows = 0,', 'long long verify_cross_options = 0, verify_intermediate = 0, verify_windows = 0,',1)
needle2='                cross_options[a] = prepare_cross(a,ea); cross_epoch[a] = epoch;'
check=r'''
                if ((cross_rows & 127) == 0) {
                    const u64 saved_a = mask[ea], saved_pol = pol;
                    mask[ea] &= ~(1ULL << a);
                    for (u64 windows = hm; windows; windows &= windows-1) {
                        const int b = __builtin_ctzll(windows);
                        for (int code = 0; code < 30; ++code) {
                            const int e = code%15;
                            if (e == ea) continue;
                            const u64 saved_b = mask[e];
                            mask[e] |= 1ULL << b;
                            pol = (saved_pol & ~(1ULL << b)) | (u64(code/15)<<b);
                            int lost = 0;
                            for (int p : selected) {
                                uint32_t r; int cost;
                                pair_state(pairs.au[p],pairs.diff[p],r,cost);
                                lost += cost == 0;
                            }
                            assert(bool(cross_options[a][b] >> code & 1) == (lost < kRejectLoss));
                            ++verify_cross_options;
                            mask[e] = saved_b;
                        }
                    }
                    mask[ea] = saved_a; pol = saved_pol;
                }
'''
if 'cross_zero' in s:
    check=check.replace('                            ++verify_cross_options;', '''                            assert(bool(cross_zero[a][b] >> code & 1) == (lost == 0));
                            assert(bool(cross_one[a][b] >> code & 1) == (lost == 1));
                            ++verify_cross_options;''')
if needle2 in s:s=s.replace(needle2,needle2+check,1)
needle2='''        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);'''
check=r'''
        if ((accepted & 127) == 0) {
            for (int p = 0; p < np; ++p) {
                uint32_t r; int cost;
                pair_state(pairs.au[p],pairs.diff[p],r,cost);
                assert(r == pairs.dir[p]); assert(cost == pairs.rel[p]);
                ++verify_intermediate;
            }
        }
'''
assert needle2 in s;s=s.replace(needle2,needle2+check,1)
s=s.replace('    stats.gobj_after = cur;', '    std::cerr << "verify_cross_options = " << verify_cross_options << "\\nverify_intermediate = " << verify_intermediate << std::endl;\n    stats.gobj_after = cur;',1)
(here/'verify-check.cpp').write_text(s)
