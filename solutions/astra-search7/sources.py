"""同じ状態では、候補の尽きた交換元窓を引き直さない。"""
def sources(t,mode):
    helper=r'''    std::array<u64,2> source_options{};
    std::array<unsigned,2> source_epoch{};
    long long source_empty=0;
    auto choose_source = [&](int kind) __attribute__((target("popcnt"))) {
        if (source_epoch[kind]!=epoch) {
            source_options[kind]=kActiveWindows&~hm; source_epoch[kind]=epoch;
        }
        u64 bits=source_options[kind];
        if (!bits) { ++source_empty; return -1; }
        int skip=rng.below(__builtin_popcountll(bits));
        while (skip--) bits&=bits-1;
        return __builtin_ctzll(bits);
    };
'''
    t=t.replace('    auto propose = [&](Move& mv) {',helper+'    auto propose = [&](Move& mv) {',1)
    if mode&1:
        needle='''        } else if (swindow) {  // generic window a <-> handle window b
            int color ='''
        new='''        } else if (swindow) {  // generic window a <-> handle window b
            if (selected.size()==unsigned(need)) {
                a=choose_source(0); if (a<0) return false;
                ia=0; while (order[ia]!=a) ++ia;
                ea=eb=which[a]; olda=oldb=mask[ea];
            }
            int color ='''
        assert needle in t;t=t.replace(needle,new,1)
        t=t.replace('                if (!(options[0] | options[1])) return false;', '                if (!(options[0] | options[1])) { source_options[0]&=~(1ULL<<a); return false; }',1)
        needle='                window_options[a][color] &= ~(1ULL << b);'
        t=t.replace(needle,needle+'\n                if (!(window_options[a][0]|window_options[a][1])) source_options[0]&=~(1ULL<<a);',1)
    if mode&2:
        needle='''        } else {  // window a to another pair
            if (counts[ea] < 2) return false;'''
        new='''        } else {  // window a to another pair
            if (selected.size()==unsigned(need)) {
                a=choose_source(1); if (a<0) return false;
                ia=0; while (order[ia]!=a) ++ia;
                ea=which[a]; olda=mask[ea];
            }
            if (counts[ea] < 2) { source_options[1]&=~(1ULL<<a); return false; }'''
        assert needle in t;t=t.replace(needle,new,1)
        t=t.replace('                if (!available) return false;', '                if (!available) { source_options[1]&=~(1ULL<<a); return false; }',1)
        needle='                if (true) transfer_options[a] &= ~(1U << code);'
        t=t.replace(needle,needle+'\n                if (!transfer_options[a]) source_options[1]&=~(1ULL<<a);',1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "source_empty = " << source_empty << '\n';
    stats.gobj_after = cur;''',1)
    return t
