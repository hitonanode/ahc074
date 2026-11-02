"""現在の高費用の対を少数だけ事前損失数から除き、入れ替えを許す。"""
def protect(t,ignore):
    t=t.replace('    bool screen_dirty = true;', '''    bool screen_dirty = true;
    std::vector<unsigned> unprotected_epoch(np,0);
    unsigned protection_epoch=0;
    Bits protected_bits{};
    auto prepare_protection = [&] __attribute__((target("popcnt"))) {
        if (protection_epoch==epoch) return;
    };''',1) if False else t
    # epoch must be declared before every screen and candidate helper.
    t=t.replace('    unsigned epoch = 1;', '')
    needle='    bool screen_dirty = true;'
    code='''    unsigned epoch = 1;
    std::vector<unsigned> unprotected_epoch(np,0);
    unsigned protection_epoch=0;
    Bits protected_bits{};
    auto prepare_protection = [&]() __attribute__((target("popcnt"))) {
        if (protection_epoch==epoch) return;
        protection_epoch=epoch;
        if (selected.size()!=unsigned(need)) return;
        std::array<std::pair<int,int>,128> ranked;
        for (int i=0;i<need;++i) {
            const int p=selected[i];
            const int cost=1800*__builtin_popcountll(pairs.diff[p]&hm)+5*(pairs.rel[p]-1)+full144[p];
            ranked[i]={cost,p};
        }
        std::nth_element(ranked.begin(),ranked.begin()+need-IGNORE,ranked.begin()+need);
        for (int i=need-IGNORE;i<need;++i) unprotected_epoch[ranked[i].second]=epoch;
    };
'''.replace('IGNORE',str(ignore))
    assert needle in t;t=t.replace(needle,needle+'\n'+code,1)
    t=t.replace('    auto propose = [&](Move& mv) {','    auto propose = [&](Move& mv) {\n        prepare_protection();',1)
    needle='            screen_dirty = false;'
    t=t.replace(needle,'''            protected_bits={};
            for (int i=0;i<int(selected.size());++i)
                if (unprotected_epoch[selected[i]]!=epoch) protected_bits[i>>6]|=1ULL<<(i&63);
'''+needle,1)
    t=t.replace('''lost += __builtin_popcountll((match_colors[b][c][w] & forbidden[a][0][w]) |
                                         (match_colors[b][c ^ 1][w] & forbidden[a][1][w]));''','''lost += __builtin_popcountll(((match_colors[b][c][w] & forbidden[a][0][w]) |
                                         (match_colors[b][c ^ 1][w] & forbidden[a][1][w])) & protected_bits[w]);''',1)
    old='''loss += __builtin_popcountll((match_colors[b][color][w] & forbidden[a][0][w]) |
                                                (match_colors[b][color^1][w] & forbidden[a][1][w]));'''
    new='''loss += __builtin_popcountll(((match_colors[b][color][w] & forbidden[a][0][w]) |
                                                (match_colors[b][color^1][w] & forbidden[a][1][w])) & protected_bits[w]);'''
    assert old in t;t=t.replace(old,new,1)
    t=t.replace('        for (int p : selected) {','        for (int p : selected) {\n            if (unprotected_epoch[p]==epoch) continue;')
    # The scalar screen has deeper indentation but shares the matched substring.
    return t
