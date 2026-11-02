"""汎用窓の交換・反転を、直接矛盾のビット集合で先に除外する。"""
def direct(t):
    start=t.index('    auto swap_losses =')
    body=t.index('        if (screen_dirty)',start)
    end=t.index('        const int a = mv.a, e = mv.ea;',body)
    refresh=t[body:end]
    t=t[:start]+'    auto refresh_screen = [&] {\n'+refresh+'    };\n'+t[start:body]+'        refresh_screen();\n'+t[end:]
    needle='    auto propose = [&](Move& mv) {'
    helper=r'''    long long direct_screen_rejects=0;
    auto direct_losses = [&](int ea,int eb) __attribute__((target("popcnt"))) {
        refresh_screen();
        Bits bad{};
        for (int e : {ea,eb}) {
            Colors arcs{};
            for (u64 q=mask[e];q;q&=q-1) {
                const int a=__builtin_ctzll(q), color=(pol>>a)&1;
                for (int w=0;w<2;++w) {
                    arcs[0][w]|=match_colors[a][color][w];
                    arcs[1][w]|=match_colors[a][color^1][w];
                }
            }
            for (int w=0;w<2;++w) bad[w]|=arcs[0][w]&arcs[1][w];
            if (ea==eb) break;
        }
        return __builtin_popcountll(bad[0])+__builtin_popcountll(bad[1]);
    };
'''
    t=t.replace(needle,helper+needle,1)
    needle='''        if (selected.size() == unsigned(need) && !swindow && transfer < 0) {
            int lost = 0;'''
    new='''        if (selected.size() == unsigned(need) && !swindow && transfer < 0) {
            if (direct_losses(ea,eb)>=kRejectLoss) {
                mask[ea]=olda; mask[eb]=oldb; pol=oldpol;
                ++screen_rejected; ++direct_screen_rejects;
                memo_epoch[move_key]=2*epoch;
                return false;
            }
            int lost = 0;'''
    assert needle in t;t=t.replace(needle,new,1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "direct_screen_rejects = " << direct_screen_rejects << '\n';
    stats.gobj_after = cur;''',1)
    return t
