#!/usr/bin/env python3
"""採用ソースの閉路ビット集合と目的値キャッシュを、直接計算とのassertで検査するコピーを作る。"""
from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'main.cpp').read_text()
s=s.replace('constexpr double kHelperGiveUp = 1.55;', 'constexpr double kHelperGiveUp = 1000.0;')
(p/'verify-reference.cpp').write_text(s)
s=s.replace('    auto swap_losses =', '    long long verify_losses = 0, verify_memo = 0;\n    auto swap_losses =',1)
s=s.replace('        return lost;\n    };', '''        int direct_lost = 0;
        for (int p : selected) {
            const u64 q = pairs.diff[p] & mask[e], z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & uint32_t(~(fwd[e] | rev[e]));
            if (q & ~z) r |= fwd[e];
            if (q & z) r |= rev[e];
            direct_lost += !relations.cost(r);
        }
        assert(direct_lost == lost);
        ++verify_losses;
        return lost;
    };''',1)
s=s.replace('if (memo_hit) { memo_hits++; return true; }', 'if (memo_hit) memo_hits++;',1)
line='const double candidate = memo_hit ? memo_value[move_key] : matching_cost(nrel.data(), handles_after(mv));'
s=s.replace(line,line+'''
        if (memo_hit) {
            const double direct_value = matching_cost(nrel.data(), handles_after(mv));
            assert(direct_value == candidate);
            ++verify_memo;
        }''')
s=s.replace('    stats.gobj_after = cur;', '''    std::cerr << "verify_losses = " << verify_losses << "\\nverify_memo = " << verify_memo << '\\n';
    stats.gobj_after = cur;''',1)
(p/'verify-check.cpp').write_text(s)
print('Generated verify-reference.cpp and verify-check.cpp; compile both with -DSIM_HARNESS.')
