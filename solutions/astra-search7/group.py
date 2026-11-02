"""比較器の組を丸ごと交換する。直接の矛盾を保存し、DAGの構造だけを変える。"""
def group(t,rate):
    t=t.replace('        u64 olda, oldb, oldpol;', '        u64 olda, oldb, oldpol;\n        int group_code = -1;')
    helper=r'''    std::array<u64,15> group_options{};
    std::array<unsigned,15> group_epoch{};
    long long group_rows=0, group_samples=0, group_accepts=0;
    auto group_key = [](int ea, int eb, int flags) {
        if (ea>eb) { std::swap(ea,eb); flags=(flags>>1)|((flags&1)<<1); }
        return 147456+4*(15*ea+eb)+flags;
    };
    auto prepare_group = [&](int ea) {
        u64 options=0;
        for (int eb=0; eb<ne; ++eb) if (ea!=eb) {
            const uint32_t keep=~uint32_t(fwd[ea]|rev[ea]|fwd[eb]|rev[eb]);
            for (int flags=0; flags<4; ++flags) {
                int lost=0;
                for (int p:selected) {
                    const uint32_t old=pairs.dir[p];
                    unsigned da=((old>>ea)&1)|(((old>>(16+ea))&1)<<1);
                    unsigned db=((old>>eb)&1)|(((old>>(16+eb))&1)<<1);
                    if (flags&1) da=(da>>1)|((da&1)<<1);
                    if (flags&2) db=(db>>1)|((db&1)<<1);
                    const uint32_t r=(old&keep)|((da&1)<<eb)|((da>>1)<<(16+eb))
                                          |((db&1)<<ea)|((db>>1)<<(16+ea));
                    if (!relations.cost(r) && ++lost>=kRejectLoss) break;
                }
                if (lost<kRejectLoss) options |= 1ULL<<(eb+15*flags);
            }
        }
        ++group_rows;
        return options;
    };
'''
    t=t.replace('    auto propose = [&](Move& mv) {',helper+'    auto propose = [&](Move& mv) {',1)
    needle='        int transfer = -1;'
    t=t.replace(needle,needle+'''
        int group_code=-1;
        const bool group_move = !swindow && kind>=3 && kind<8 && selected.size()==unsigned(need) && rng.mod(RATE)==0;'''.replace('RATE',str(rate)),1)
    needle='        } else if (kind < 8) {  // exchange the pairs of a and b'
    block='''        } else if (group_move) {
            if (group_epoch[ea]!=epoch) {
                group_options[ea]=prepare_group(ea); group_epoch[ea]=epoch;
            }
            u64 options=group_options[ea];
            if (!options) return false;
            int skip=rng.below(__builtin_popcountll(options));
            while (skip--) options &= options-1;
            const int code=__builtin_ctzll(options);
            group_options[ea] &= ~(1ULL<<code);
            eb=code%15; group_code=code/15; oldb=mask[eb];
            // Preserve all windows and each group's internal agreement, while changing
            // its comparator endpoints and optionally reversing its common direction.
            mask[ea]=oldb; mask[eb]=olda;
            if (group_code&1) pol ^= olda;
            if (group_code&2) pol ^= oldb;
            ++group_samples;
'''
    assert needle in t;t=t.replace(needle,block+needle,1)
    needle='        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};'
    t=t.replace(needle,needle+'\n        mv.group_code=group_code;',1)
    t=t.replace('        if (cross_move) move_key =','        if (group_move) move_key = group_key(ea,eb,group_code);\n        else if (cross_move) move_key =',1)
    t=t.replace('&& !swindow && transfer < 0)', '&& !swindow && transfer < 0 && !group_move)',1)
    needle='''        } else {
            if (mv.kind >= 3 && mv.kind < 8) std::swap(which[mv.a], which[mv.b]);'''
    new='''        } else if (mv.group_code>=0) {
            for (u64 q=mask[mv.ea]; q; q&=q-1) which[__builtin_ctzll(q)]=mv.ea;
            for (u64 q=mask[mv.eb]; q; q&=q-1) which[__builtin_ctzll(q)]=mv.eb;
            std::swap(counts[mv.ea],counts[mv.eb]);
            ++group_accepts;
        } else {
            if (mv.kind >= 3 && mv.kind < 8) std::swap(which[mv.a], which[mv.b]);'''
    assert needle in t;t=t.replace(needle,new,1)
    needle='if (mv.swindow && mv.ea != mv.eb) reverse_key ='
    assert t.count(needle)==2
    t=t.replace(needle,'''if (mv.group_code>=0) reverse_key=group_key(mv.ea,mv.eb,(mv.group_code>>1)|((mv.group_code&1)<<1));
            else if (mv.swindow && mv.ea != mv.eb) reverse_key =''')
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "group_rows = " << group_rows << "\ngroup_samples = " << group_samples
              << "\ngroup_accepts = " << group_accepts << '\n';
    stats.gobj_after = cur;''',1)
    return t
