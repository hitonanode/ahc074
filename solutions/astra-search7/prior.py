"""既存候補の損失数を提案順に反映する。受理目的値は変更しない。"""
def transfer_prior(t,penalty):
    old='            transfer_priority[a][code] = cost;'
    new=f'''            // The old ranking treated a lost selected pair as zero extra generic cost.
            // Charge a proposal-only penalty; the complete matching is still evaluated unchanged.
            transfer_priority[a][code] = cost + {penalty} * int(((ones>>code)&1) + 2*((twos>>code)&1));'''
    assert old in t;return t.replace(old,new,1)

def window_prior(t,weight):
    t=t.replace('    std::array<Bits, 64> window_options{};', '    std::array<Bits, 64> window_options{}, window_zero{}, window_one{};',1)
    t=t.replace('        Bits available{};', '        Bits available{}; window_zero[a]={}; window_one[a]={};',1)
    needle='                if (loss < kRejectLoss) available[color] |= 1ULL << b;'
    assert needle in t;t=t.replace(needle,needle+'''
                if (loss==0) window_zero[a][color] |= 1ULL<<b;
                if (loss==1) window_one[a][color] |= 1ULL<<b;''',1)
    old='''                int skip = rng.below(__builtin_popcountll(options[0]) + __builtin_popcountll(options[1]));
                const int first = __builtin_popcountll(options[0]);
                color = skip >= first;
                if (color) skip -= first;
                u64 bits = options[color];
                while (skip--) bits &= bits-1;
                b = __builtin_ctzll(bits);'''
    new='''                std::array<Bits,3> classes;
                std::array<int,3> count{};
                for (int c=0;c<2;++c) {
                    classes[0][c]=options[c]&window_zero[a][c];
                    classes[1][c]=options[c]&window_one[a][c];
                    classes[2][c]=options[c]&~(window_zero[a][c]|window_one[a][c]);
                    for (int l=0;l<3;++l) count[l]+=__builtin_popcountll(classes[l][c]);
                }
                constexpr int weights[3]={W0,W1,1};
                int level=0,skip=rng.below(weights[0]*count[0]+weights[1]*count[1]+count[2]);
                while (skip>=weights[level]*count[level]) { skip-=weights[level]*count[level]; ++level; }
                skip/=weights[level];
                const int first=__builtin_popcountll(classes[level][0]);
                color=skip>=first;
                if (color) skip-=first;
                u64 bits=classes[level][color];
                while (skip--) bits&=bits-1;
                b=__builtin_ctzll(bits);'''.replace('W0',str(weight*weight)).replace('W1',str(weight))
    assert old in t;t=t.replace(old,new,1)
    return t
