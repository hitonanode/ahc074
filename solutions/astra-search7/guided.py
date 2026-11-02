"""現在のマッチングで使わない商品を新しく対にできる窓交換を提案する。"""
def guided(t,rate,tolerance=1800,unmatched=True):
    t=t.replace('        u64 olda, oldb, oldpol;', '        u64 olda, oldb, oldpol;\n        bool guided = false;')
    helper=r'''    std::vector<int> guide_pairs;
    unsigned guide_epoch=0;
    int guide_limit=0;
    long long guide_rows=0, guide_attempts=0, guide_samples=0, guide_accepts=0;
    // A newly compatible cheap edge between unmatched vertices can replace an expensive
    // selected edge. Use that as a proposal guide only; evaluate the full matching as usual.
    auto choose_guided = [&](int& out_a,int& out_b,int& out_color) __attribute__((target("popcnt"))) {
        if (guide_epoch!=epoch) {
            std::array<bool,256> used{};
            guide_limit=0;
            for (int p:selected) {
                used[pairs.u[p]]=used[pairs.v[p]]=true;
                const int key=1800*__builtin_popcountll(pairs.diff[p]&hm)+5*(pairs.rel[p]-1)+full144[p];
                guide_limit=std::max(guide_limit,key);
            }
            guide_pairs.clear();
            for (int p=0;p<np;++p) {
                if (pairs.rel[p] || UNMATCHED) continue;
                const unsigned both=pairs.dir[p]&(pairs.dir[p]>>16);
                if (both&(both-1)) continue; // A single deletion cannot fix two conflicting groups.
                const int lower=1800*__builtin_popcountll(pairs.diff[p]&hm)+full144[p];
                if (lower+5400<guide_limit) guide_pairs.push_back(p);
            }
            guide_epoch=epoch; ++guide_rows;
        }
        if (guide_pairs.empty()) return false;
        ++guide_attempts;
        const int at=rng.below(guide_pairs.size()), p=guide_pairs[at];
        guide_pairs[at]=guide_pairs.back(); guide_pairs.pop_back();
        const uint32_t old=pairs.dir[p], both=old&(old>>16);
        const u64 diff=pairs.diff[p], z=pairs.au[p]^pol;
        u64 removable=0;
        if (both) {
            const int e=__builtin_ctz(both);
            const u64 q=diff&mask[e], f=q&~z, r=q&z;
            if (f && !(f&(f-1))) removable|=f;
            if (r && !(r&(r-1))) removable|=r;
        } else removable=diff&~hm&kActiveWindows;
        struct Choice { int a,b,color,key; };
        std::array<Choice,4096> choices;
        int count=0, best_key=guide_limit;
        const int old_hd=__builtin_popcountll(diff&hm);
        for (u64 q=removable; q; q&=q-1) {
            const int a=__builtin_ctzll(q), ea=which[a];
            const u64 rest=diff&(mask[ea]&~(1ULL<<a));
            uint32_t r=old & ~uint32_t(fwd[ea]|rev[ea]);
            if (rest&~z) r|=fwd[ea];
            if (rest&z) r|=rev[ea];
            if (!relations.cost(r)) continue;
            if (window_epoch[a]!=epoch) {
                window_options[a]=prepare_windows(a,ea); window_epoch[a]=epoch;
            }
            for (int color=0;color<2;++color) {
                for (u64 bits=window_options[a][color]; bits; bits&=bits-1) {
                    const int b=__builtin_ctzll(bits);
                    uint32_t nr=r;
                    if (diff>>b&1) nr|=((pairs.au[p]>>b&1)==unsigned(color)) ? fwd[ea]:rev[ea];
                    const int rel=relations.cost(nr);
                    if (!rel) continue;
                    const int hd=old_hd+1-int(diff>>b&1);
                    const int key=1800*hd+5*(rel-1)+full144[p];
                    if (key>=guide_limit) continue;
                    best_key=std::min(best_key,key);
                    choices[count++]={a,b,color,key};
                }
            }
        }
        if (!count) return false;
        int num=0;
        for (int i=0;i<count;++i) if (choices[i].key<=best_key+TOLERANCE) choices[num++]=choices[i];
        const auto choice=choices[rng.below(num)];
        out_a=choice.a; out_b=choice.b; out_color=choice.color;
        window_options[out_a][out_color]&=~(1ULL<<out_b);
        return true;
    };
'''.replace('TOLERANCE',str(tolerance)).replace('UNMATCHED','used[pairs.u[p]] || used[pairs.v[p]]' if unmatched else 'false')
    t=t.replace('    auto propose = [&](Move& mv) {',helper+'    auto propose = [&](Move& mv) {',1)
    needle='        const bool cross_move ='
    i=t.index(needle)
    t=t[:i]+'''        const bool guided_move = swindow && selected.size()==unsigned(need) && rng.mod(RATE)==0;
'''.replace('RATE',str(rate))+t[i:]
    t=t.replace('const bool cross_move = swindow', 'const bool cross_move = !guided_move && swindow',1)
    needle='        if (cross_move) {'
    new='''        if (guided_move) {
            int color=0;
            if (!choose_guided(a,b,color)) return false;
            ia=0; while (order[ia]!=a) ++ia;
            ib=g; while (order[ib]!=b) ++ib;
            ea=eb=which[a]; olda=oldb=mask[ea];
            mask[ea] ^= (1ULL<<a)|(1ULL<<b);
            pol=(pol & ~(1ULL<<b)) | (u64(color)<<b);
            ++guide_samples;
        } else if (cross_move) {'''
    t=t.replace(needle,new,1)
    needle='        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};'
    t=t.replace(needle,needle+'\n        mv.guided=guided_move;',1)
    t=t.replace('        accepted++;', '        accepted++;\n        guide_accepts += mv.guided;',1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "guide_rows = " << guide_rows << "\nguide_attempts = " << guide_attempts
              << "\nguide_samples = " << guide_samples << "\nguide_accepts = " << guide_accepts << '\n';
    stats.gobj_after = cur;''',1)
    return t
