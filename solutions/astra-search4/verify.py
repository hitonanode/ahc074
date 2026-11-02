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
            int exact = 0;
            for (int p : selected) {
                uint32_t r; int cost;
                pair_state(pairs.au[p], pairs.diff[p], r, cost);
                exact += cost == 0;
            }
            assert(lost == exact);
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
(here/'verify-check.cpp').write_text(s)
