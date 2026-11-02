"""窓交換と比較器組の変更をまとめ、失う対が少ない複合手を列挙。"""
def cross(t, rate):
 t=t.replace('kMemoSize = 1 << 14','kMemoSize = 1 << 18')
 assert 'kMemoSize = 1 << 18' in t
 code=r'''    std::array<std::array<uint32_t,64>,64> cross_options{};
    std::array<unsigned,64> cross_epoch{};
    long long cross_rows=0, cross_samples=0, cross_accepts=0;
    auto prepare_cross = [&](int a, int ea) __attribute__((target("bmi2,popcnt"))) {
        std::array<uint32_t,64> ones{}, twice{}, rejected{}, options{};
        const u64 rest = mask[ea] & ~(1ULL << a);
        const uint32_t keep = ~uint32_t(fwd[ea] | rev[ea]);
        for (int p : selected) {
            const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & keep;
            if (q & ~z) r |= fwd[ea];
            if (q & z) r |= rev[ea];
            const u64 c = closure(r);
            const uint32_t forward = _pext_u64(c,0x0000010101010100ULL)
                | (_pext_u64(c,0x0000020202020000ULL)<<5)
                | (_pext_u64(c,0x0000040404000000ULL)<<9)
                | (_pext_u64(c,0x0000080800000000ULL)<<12) | (((c>>44)&1)<<14);
            const uint32_t reverse = _pext_u64(c,0x00002030383c3eULL);
            for (u64 windows = pairs.diff[p]&hm; windows; windows &= windows-1) {
                const int b = __builtin_ctzll(windows);
                const uint32_t bad = (pairs.au[p] >> b & 1) ? reverse | (forward<<15) : forward | (reverse<<15);
                // Parallel counters saturate when a third selected pair becomes incompatible.
                rejected[b] |= twice[b]&bad; twice[b] |= ones[b]&bad; ones[b] ^= bad;
            }
        }
        const uint32_t allowed = ((1U<<30)-1) & ~((1U<<ea) | (1U<<(ea+15)));
        for (u64 windows = hm; windows; windows &= windows-1) {
            const int b = __builtin_ctzll(windows);
            options[b] = allowed & ~rejected[b];
        }
        ++cross_rows;
        return options;
    };
'''
 t=t.replace('    auto propose =',code+'    auto propose =',1)
 needle='''        if (swindow) {  // generic window a <-> handle window b'''
 code=r'''        const bool cross_move = swindow && counts[ea] >= 2 && selected.size() == unsigned(need) && rng.mod(CROSS_RATE)==0;
        if (cross_move) {
            if (cross_epoch[a] != epoch) {
                cross_options[a] = prepare_cross(a,ea); cross_epoch[a] = epoch;
            }
            int total = 0;
            for (u64 windows = hm; windows; windows &= windows-1) total += __builtin_popcount(cross_options[a][__builtin_ctzll(windows)]);
            if (!total) return false;
            int skip = rng.below(total), code = 0;
            for (u64 windows = hm; windows; windows &= windows-1) {
                b = __builtin_ctzll(windows);
                const int count = __builtin_popcount(cross_options[a][b]);
                if (skip >= count) { skip -= count; continue; }
                uint32_t options = cross_options[a][b];
                while (skip--) options &= options-1;
                code = __builtin_ctz(options); break;
            }
            cross_options[a][b] &= ~(1U<<code);
            eb = code%15; oldb = mask[eb];
            ib = g; while (order[ib] != b) ++ib;
            mask[ea] &= ~(1ULL<<a); mask[eb] |= 1ULL<<b;
            pol = (pol & ~(1ULL<<b)) | (u64(code/15)<<b);
            ++cross_samples;
        } else if (swindow) {  // generic window a <-> handle window b'''.replace('CROSS_RATE',str(rate))
 assert needle in t;t=t.replace(needle,code,1)
 t=t.replace('        if (swindow) move_key =', '''        if (cross_move) move_key = 16384 + 2*(ne*(64*a+b)+eb) + int(pol>>b&1);
        else if (swindow) move_key =''',1)
 t=t.replace('''            which[mv.b] = mv.ea;''', '''            which[mv.b] = mv.eb;
            if (mv.ea != mv.eb) { --counts[mv.ea]; ++counts[mv.eb]; ++cross_accepts; }''',1)
 needle='''            if (mv.swindow) reverse_key ='''
 code='''            if (mv.swindow && mv.ea != mv.eb) reverse_key = 16384 + 2*(ne*(64*mv.b+mv.a)+mv.ea) + int(mv.oldpol>>mv.a&1);
            else if (mv.swindow) reverse_key ='''
 assert t.count(needle)==2;t=t.replace(needle,code)
 t=t.replace('    stats.gobj_after = cur;', '''    std::cerr << "cross_rows = " << cross_rows << "\\ncross_samples = " << cross_samples << "\\ncross_accepts = " << cross_accepts << '\\n';
    stats.gobj_after = cur;''',1)
 return t

def cached_cross(t):
    # Extract the screen refresh unchanged, then share its closures with the compound move.
    begin=t.index('        if (screen_dirty) {',t.index('    auto swap_losses ='))
    end=t.index('        const int a = mv.a, e = mv.ea;',begin)
    refresh=t[begin:end]
    t=t[:begin]+'        refresh_screen();\n'+t[end:]
    place=t.index('    auto swap_losses =')
    t=t[:place]+'    auto refresh_screen = [&]() __attribute__((target("popcnt"))) {\n'+refresh+'    };\n'+t[place:]
    a=t.index('    auto prepare_cross =');b=t.index('    auto propose =',a)
    part=t[a:b]
    part=part.replace('        std::array<uint32_t,64> ones{}, twice{}, rejected{}, options{};', '        refresh_screen();\n        std::array<uint32_t,64> ones{}, twice{}, rejected{}, options{};')
    part=part.replace('        for (int p : selected) {', '        for (int i = 0; i < int(selected.size()); ++i) {\n            const int p = selected[i];',1)
    part=part.replace('            const u64 c = closure(r);', '''            // Most pairs keep the same last arc after removing a; their closure is shared.
            const u64 c = r == pairs.dir[p] ? match_closed[i] : closure(r);''',1)
    t=t[:a]+part+t[b:]
    return t

def rank_cross(t, mode):
    t=t.replace('    std::array<unsigned,64> cross_epoch{};', '''    std::array<std::array<uint32_t,64>,64> cross_zero{}, cross_one{};
    std::array<unsigned,64> cross_epoch{};''',1)
    t=t.replace('            options[b] = allowed & ~rejected[b];', '''            options[b] = allowed & ~rejected[b];
            cross_zero[a][b] = options[b] & ~(ones[b] | twice[b]);
            cross_one[a][b] = options[b] & ones[b] & ~twice[b];''',1)
    a=t.index('            int total = 0;',t.index('        if (cross_move) {'))
    b=t.index('            cross_options[a][b] &=',a)
    code=r'''            std::array<int,3> totals{};
            auto options_at = [&](int b, int level) {
                uint32_t bits = cross_options[a][b];
                if (level == 0) bits &= cross_zero[a][b];
                if (level == 1) bits &= cross_one[a][b];
                if (level == 2) bits &= ~(cross_zero[a][b] | cross_one[a][b]);
                return bits;
            };
            for (u64 windows = hm; windows; windows &= windows-1) {
                const int b = __builtin_ctzll(windows);
                for (int level = 0; level < 3; ++level) totals[level] += __builtin_popcount(options_at(b,level));
            }
            if (!(totals[0]+totals[1]+totals[2])) return false;
            int level = 0, skip = 0;
PICK
            int code = 0;
            for (u64 windows = hm; windows; windows &= windows-1) {
                b = __builtin_ctzll(windows);
                uint32_t options = options_at(b,level);
                const int count = __builtin_popcount(options);
                if (skip >= count) { skip -= count; continue; }
                while (skip--) options &= options-1;
                code = __builtin_ctz(options); break;
            }
'''
    if mode==1:
        choose='''            while (!totals[level]) ++level;
            skip = rng.below(totals[level]);'''
    else:
        choose='''            // Loss classes 0/1/2 receive 4/2/1 tickets per eligible direction.
            skip = rng.below(4*totals[0]+2*totals[1]+totals[2]);
            while (skip >= (totals[level] << (2-level))) {
                skip -= totals[level] << (2-level); ++level;
            }
            skip >>= 2-level;'''
    t=t[:a]+code.replace('PICK',choose)+t[b:]
    return t
