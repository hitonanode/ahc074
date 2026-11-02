"""同じ組の2汎用窓を2ハンドル窓へ入れ替える候補を全列挙する。"""
def double(t,rate):
    t=t.replace('kMemoSize = 1 << 18', 'kMemoSize = 1 << 19')
    t=t.replace('        u64 olda, oldb, oldpol;','        u64 olda, oldb, oldpol;\n        int a2 = -1, b2 = -1;')
    needle='    std::vector<unsigned> tabu_epoch(kMemoSize, 0);'
    assert t.count(needle)==1;t=t.replace(needle,'')
    needle='    auto propose = [&](Move& mv) {'
    helper=r'''    std::vector<unsigned> tabu_epoch(kMemoSize, 0);
    std::vector<u64> double_signatures(1<<16, ~0ULL);
    long long double_rows = 0, double_choices = 0, double_samples = 0, double_accepts = 0;
    // Full keys distinguish both deleted windows, both inserted windows and their colors.
    // Separate slots avoid collisions with ordinary moves. A collision can discard an
    // expired cache entry, but never reuse an objective for a different move.
    auto double_key = [&](int a, int c, int b, int d, u64 newpol) {
        if (a>c) std::swap(a,c);
        if (b>d) std::swap(b,d);
        const u64 sig = a | (u64(c)<<6) | (u64(b)<<12) | (u64(d)<<18)
                      | (((newpol>>b)&1)<<24) | (((newpol>>d)&1)<<25);
        unsigned hash = ((sig * 0x9e3779b97f4a7c15ULL)>>32)&65535;
        while (double_signatures[hash] != sig) {
            const unsigned slot = (1<<18)+hash;
            if (memo_epoch[slot] < 2*epoch && tabu_epoch[slot] <= epoch) {
                double_signatures[hash] = sig; memo_epoch[slot]=0; tabu_epoch[slot]=0;
                break;
            }
            hash = (hash+1)&65535;
        }
        return int((1<<18)+hash);
    };
    auto prepare_double = [&](int a, int c, int ea) __attribute__((target("popcnt"))) {
        Move probe{}; probe.a=a; probe.b=__builtin_ctzll(hm); probe.ea=ea;
        probe.olda=mask[ea]; probe.oldpol=pol;
        swap_losses(probe); // Refresh the matching's bit positions before using match_colors.
        Colors ban{};
        const u64 rest = mask[ea] & ~((1ULL<<a)|(1ULL<<c));
        const uint32_t keep = ~uint32_t(fwd[ea]|rev[ea]);
        const auto [x,y]=ep[ea];
        for (int i=0; i<int(selected.size()); ++i) {
            const int p=selected[i];
            const u64 q=pairs.diff[p]&rest, z=pairs.au[p]^pol;
            uint32_t r=pairs.dir[p]&keep;
            if (q&~z) r|=fwd[ea];
            if (q&z) r|=rev[ea];
            const u64 closed=closure(r), bit=1ULL<<(i&63);
            if (closed>>(8*y+x)&1) ban[0][i>>6]|=bit;
            if (closed>>(8*x+y)&1) ban[1][i>>6]|=bit;
        }
        std::array<Colors,64> bad{};
        for (u64 q=hm; q; q&=q-1) {
            const int b=__builtin_ctzll(q);
            for (int color=0; color<2; ++color)
                for (int w=0; w<2; ++w)
                    bad[b][color][w] = (match_colors[b][color][w]&ban[0][w]) |
                                      (match_colors[b][color^1][w]&ban[1][w]);
        }
        std::array<int,8192> choices;
        int count=0;
        for (u64 q=hm; q; q&=q-1) {
            const int b=__builtin_ctzll(q);
            for (u64 r=q&(q-1); r; r&=r-1) {
                const int d=__builtin_ctzll(r);
                for (int cb=0; cb<2; ++cb) for (int cd=0; cd<2; ++cd) {
                    int lost=0;
                    for (int w=0; w<2; ++w) {
                        // Both insertions use the same edge. Besides cycles against the
                        // remaining DAG, opposite new directions conflict with each other.
                        const u64 conflict = (match_colors[b][cb][w]&match_colors[d][cd^1][w]) |
                                             (match_colors[b][cb^1][w]&match_colors[d][cd][w]);
                        lost += __builtin_popcountll(bad[b][cb][w]|bad[d][cd][w]|conflict);
                    }
                    if (lost<kRejectLoss) choices[count++]=b | (d<<6) | (cb<<12) | (cd<<13);
                }
            }
        }
        ++double_rows; double_choices += count;
        if (!count) return -1;
        return choices[rng.below(count)];
    };
'''
    t=t.replace(needle,helper+needle,1)
    needle='        const bool cross_move ='
    i=t.index(needle)
    t=t[:i]+'''        int double_a=-1, double_b=-1;
        const bool double_move = swindow && counts[ea]>=2 && selected.size()==unsigned(need) && rng.mod(RATE)==0;
'''.replace('RATE',str(rate))+t[i:]
    t=t.replace('const bool cross_move = swindow', 'const bool cross_move = !double_move && swindow',1)
    needle='        if (cross_move) {'
    code='''        if (double_move) {
            u64 candidates=olda & ~(1ULL<<a);
            int skip=rng.below(__builtin_popcountll(candidates));
            while (skip--) candidates &= candidates-1;
            double_a=__builtin_ctzll(candidates);
            const int code=prepare_double(a,double_a,ea);
            if (code<0) return false;
            b=code&63; double_b=(code>>6)&63;
            ib=g; while (order[ib]!=b) ++ib;
            mask[ea]=(olda & ~((1ULL<<a)|(1ULL<<double_a))) | (1ULL<<b) | (1ULL<<double_b);
            pol=(pol & ~((1ULL<<b)|(1ULL<<double_b))) | (u64((code>>12)&1)<<b) | (u64((code>>13)&1)<<double_b);
            ++double_samples;
        } else if (cross_move) {'''
    t=t.replace(needle,code,1)
    needle='        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};'
    t=t.replace(needle,needle+'\n        mv.a2=double_a; mv.b2=double_b;',1)
    t=t.replace('        if (cross_move) move_key =','        if (double_move) move_key = double_key(a,double_a,b,double_b,pol);\n        else if (cross_move) move_key =',1)
    old='    auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };'
    new='''    auto handles_after = [&](const Move& mv) {
        return hm ^ (mv.swindow ? (1ULL<<mv.a)|(1ULL<<mv.b) : 0)
                  ^ (mv.a2>=0 ? (1ULL<<mv.a2)|(1ULL<<mv.b2) : 0);
    };'''
    assert old in t;t=t.replace(old,new,1)
    needle='            std::swap(order[mv.ia], order[mv.ib]);'
    t=t.replace(needle,needle+'''
            if (mv.a2>=0) {
                which[mv.a2]=-1; which[mv.b2]=mv.ea;
                int ia2=0, ib2=g;
                while (order[ia2]!=mv.a2) ++ia2;
                while (order[ib2]!=mv.b2) ++ib2;
                std::swap(order[ia2],order[ib2]);
                ++double_accepts;
            }''',1)
    needle='if (mv.swindow && mv.ea != mv.eb) reverse_key ='
    assert t.count(needle)==2
    t=t.replace(needle,'''if (mv.a2>=0) reverse_key=double_key(mv.b,mv.b2,mv.a,mv.a2,mv.oldpol);
            else if (mv.swindow && mv.ea != mv.eb) reverse_key =''')
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "double_rows = " << double_rows << "\ndouble_choices = " << double_choices
              << "\ndouble_samples = " << double_samples << "\ndouble_accepts = " << double_accepts << '\n';
    stats.gobj_after = cur;''',1)
    return t
