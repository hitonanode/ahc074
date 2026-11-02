from pathlib import Path
root=Path(__file__).resolve().parent
s=(root.parent/'as6-cap38/main.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:120]
 s=s.replace(a,b)
sub('constexpr int kCapWindow = 63, kCapPaper = 6;\nconstexpr u64 kCapBit = 1ULL << kCapWindow;\nconstexpr u64 kActiveWindows = kCapBit - 1;', '''#ifndef CAP_COUNT
#define CAP_COUNT 1
#endif
#ifndef CAP_WIDTH
#define CAP_WIDTH CAP_COUNT
#endif
#ifndef CAP_COLORS
#define CAP_COLORS ((1 << CAP_WIDTH) - 1)
#endif
#ifndef GENERIC_COUNT
#define GENERIC_COUNT 38
#endif
#ifndef FAST_AFTER
#define FAST_AFTER 1.68
#endif
constexpr int kCaps = CAP_COUNT, kCapWidth = CAP_WIDTH;
constexpr int kCapWindow = 64-kCapWidth, kCapPaper = 6;
constexpr u64 kActiveWindows = ~0ULL >> kCapWidth;
constexpr u64 kCapBit = ~kActiveWindows;
u64 cap_pattern = u64(CAP_COLORS) << (kCapWindow % 64);
// The top t caps overwrite a prefix of the selector coordinates. For two
// one-window caps this yields precisely the three insertion depths 0,1,2.
u64 cap_prefix(int t) {
    if (!t) return 0;
    if (kCaps == 1) return kCapBit;
    return ((1ULL << t)-1) << (kCapWindow % 64);
}
int cap_code(u64 a) { return int((a & kCapBit) >> (kCapWindow % 64)); }
std::array<std::array<int, 8>, 8> cap_print_table{};
void init_cap_table() {
    for (auto& row : cap_print_table) row.fill(-1);
    for (int a=0; a<(1<<kCapWidth); ++a) for (int b=0; b<(1<<kCapWidth); ++b) {
        int best = 1000;
        for (int p=0; p<(1<<kCapWidth); ++p) {
            int da=100, db=100;
            for (int t=0; t<=kCaps; ++t) {
                const int mask = cap_code(cap_prefix(t));
                const int z = (p & ~mask) | (cap_code(cap_pattern) & mask);
                if (z==a) da=std::min(da,t);
                if (z==b) db=std::min(db,t);
            }
            if (da<100 && db<100 && da+db<best) best=da+db, cap_print_table[a][b]=p;
        }
    }
}
bool cap_compatible(u64 a,u64 b) { return cap_print_table[cap_code(a)][cap_code(b)]>=0; }
u64 cap_print(u64 a,u64 b) {
    const int p=cap_print_table[cap_code(a)][cap_code(b)];
    assert(p>=0);
    return u64(p) << (kCapWindow % 64);
}''')
sub('256 - (191 - m)', '256 - (192 - kCaps - m)')
sub('H(63 - g), U(191 - m)', 'H(64 - kCapWidth - g), U(192 - kCaps - m)')
sub('g == 36 ? x % 27 : x % (63-g)', 'x % (64-kCapWidth-g)')
sub('if (__builtin_popcountll(d) > kCutoff) continue;', 'if (__builtin_popcountll(d & kActiveWindows) > kCutoff || !cap_compatible(A[u], A[v])) continue;')
sub('144 * __builtin_popcountll(pairs.diff[p])','144 * __builtin_popcountll(pairs.diff[p] & kActiveWindows)')
sub('hb[i] = A[i] >> G;', 'hb[i] = (A[i] & kActiveWindows) >> G;')
sub('u64 d = A[a] ^ A[b];', 'u64 d = (A[a] ^ A[b]) & kActiveWindows;')
sub('int M = 6, G = 38;  // as6-cap38: 38 generic windows', 'int M = 6, G = GENERIC_COUNT;')
sub('kFastAfter = 1.80', 'kFastAfter = FAST_AFTER')
sub('kHelperGiveUp = 1.55', 'kHelperGiveUp = 1.48')
sub('    const auto originalA = A;', '    init_cap_table();\n    const auto originalA = A;')
sub('        for (u64& a : A) a &= kActiveWindows;\n', '')
sub('return comp.compatible(a, b); }, estimate,', 'return cap_compatible(a,b) && comp.compatible(a, b); }, estimate,')
sub('    for (int u = 0; u < P; ++u) A[u] |= originalA[u] & kCapBit;', '')
sub('    papers[kCapPaper] = {kCapBit, kCapBit};', '''    for (int t=0;t<kCaps;++t) {
        const u64 mask=cap_prefix(t+1)^cap_prefix(t);
        papers[kCapPaper+t] = {mask, cap_pattern & mask};
    }''')
sub('int next = M + 1;', 'int next = M + kCaps;')
sub('            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;', '            black = (black & ~kCapBit) | cap_print(A[u.a], A[u.b>=0?u.b:u.a]);')
sub('''        const bool needs_cap = (A[adaptive_request] & kCapBit) && !(paper[d].black & kCapBit);
        if (!needs_cap) move(d, 0);
        else {
            const int cp = index_of(kCapPaper), dp = index_of(d);
            move(d, cp + int(dp > cp));
        }''', '''        for (int t=0;t<=kCaps;++t) {
            const u64 mask=cap_prefix(t);
            const u64 shown=(paper[d].black & (kCapBit & ~mask)) | (cap_pattern & mask);
            if (shown != (A[adaptive_request] & kCapBit)) continue;
            if (!t) move(d,0);
            else {
                const int cp=index_of(kCapPaper+t-1), dp=index_of(d);
                move(d,cp+int(dp>cp));
            }
            return;
        }
        invalid=true;''')
sub('if (i == 0 || (i == 1 && order[0] == kCapPaper))', '''if (std::all_of(order.begin(), order.begin()+i,
                            [](int x) { return x>=kCapPaper && x<kCapPaper+kCaps; }))''')
sub('move(k, depth + 1);', 'move(k, depth + kCaps);')
sub('move(pk.paper, 1 + pk.depth + (after_target ? 1 : 0));', 'move(pk.paper, kCaps + pk.depth + (after_target ? 1 : 0));')
sub('move(x, 1 + depth + placed + (lifted ? 1 : 0));', 'move(x, kCaps + depth + placed + (lifted ? 1 : 0));')
sub('        if (order[0] != kCapPaper) return;', '        for (int t=0;t<kCaps;++t) if (order[t] != kCapPaper+t) return;')
sub('if (order[i + 1] >= M) return;', 'if (order[i + kCaps] >= M) return;')
sub('order.begin() + 1, order.begin() + 1 + M', 'order.begin() + kCaps, order.begin() + kCaps + M')
sub('''            const auto cap_it = std::find(ord.begin(), ord.end(), kCapPaper);
            for (auto it = ord.begin(); it != cap_it; ++it) if (*it < M) return false;''', '''            // Keep every fixed cap above the whole generic layer, in its original order.
            int last_cap=-1;
            for (int t=0;t<kCaps;++t) {
                const int cp=int(std::find(ord.begin(),ord.end(),kCapPaper+t)-ord.begin());
                if (cp<=last_cap) return false;
                for (int i=0;i<cp;++i) if (ord[i]<M) return false;
                last_cap=cp;
            }''')
sub('''    solver.order.erase(solver.order.begin() + kCapPaper);
    solver.order.insert(solver.order.begin(), kCapPaper);''', '''    // Install from bottom to top; each cap is visible on its disjoint window.
    for (int t=kCaps-1;t>=0;--t) {
        const int id=kCapPaper+t;
        solver.order.erase(std::find(solver.order.begin(),solver.order.end(),id));
        solver.order.insert(solver.order.begin(),id);
    }''')
sub('tot += 1;  // first-request cap installation', 'tot += kCaps;  // first-request cap installation')
sub('if (r == 0) moves.insert(moves.begin(), {kCapPaper, 0});', 'if (r == 0) for (int t=0;t<kCaps;++t) moves.insert(moves.begin(), {kCapPaper+t, 0});')
# Diagnostics after the final design, before physical papers are printed.
needle='    // Papers: six generic sheets, the cap, then the columns 0, 1, ... (colors alternate,'
extra='''    if (env_int("MODEL_ONLY") || env_int("DETAIL")) {
        int close=0, compatible_close=0, all_ok=0, close_cap=0;
        for(int a=0;a<P;++a) for(int b=a+1;b<P;++b) {
            bool near=__builtin_popcountll((A[a]^A[b])&kActiveWindows)<=26;
            bool capok=cap_compatible(A[a],A[b]);
            bool genok=comp.compatible(A[a],A[b]);
            close+=near; close_cap+=near&&capok;
            compatible_close+=near&&capok&&genok; all_ok+=capok&&genok;
        }
        double hd=0, shallow=0, gd=0, triangle=0, extra=0, capdiff=0;
        int np=0;
        for (auto u:des->unit) {
            const int wt=des->weight(u);
            triangle+=wt*(des->H-1-u.c);
            if(u.b<0)continue;
            ++np;
            const u64 d=A[u.a]^A[u.b], h=des->hb[u.a]^des->hb[u.b];
            hd+=__builtin_popcountll(h); gd+=__builtin_popcountll(d&low_bits(G));
            shallow+=__builtin_popcountll(h&low_bits(u.c+1));
            extra+=2*__builtin_popcountll(h&low_bits(u.c+1));
            capdiff+=__builtin_popcountll(d&kCapBit);
        }
        std::cerr<<"close_pairs = "<<close<<"\\nclose_cap_pass = "<<close_cap
                 <<"\\ncompatible_close = "<<compatible_close<<"\\ncompatible_all = "<<all_ok
                 <<"\\npair_count = "<<np<<"\\npair_handle_hd = "<<hd/np
                 <<"\\npair_shallow_hd = "<<shallow/np<<"\\npair_generic_hd = "<<gd/np
                 <<"\\npair_cap_hd = "<<capdiff/np<<"\\ntriangle_holes = "<<triangle/P
                 <<"\\npair_extra_holes = "<<extra/P<<"\\nG = "<<G
                 <<"\\nH = "<<des->H<<"\\ncap_count = "<<kCaps<<"\\ncap_width = "<<kCapWidth<<'\\n';
        if (env_int("DUMP_DESIGN")) {
            std::cout<<G<<' '<<kCaps<<' '<<kCapWidth<<' '<<cap_code(cap_pattern)<<'\\n';
            for(int j=0;j<64;++j)std::cout<<permutation[j]<<' ';std::cout<<'\\n';
            for(int j=0;j<G;++j)std::cout<<comp.edge[j].first<<' '<<comp.edge[j].second<<' '<<comp.polarity[j]<<'\\n';
            for(auto a:A)std::cout<<a<<'\\n';
            for(auto h:des->handle)std::cout<<h<<' ';std::cout<<'\\n';
            for(auto u:des->unit)std::cout<<u.a<<' '<<u.b<<' '<<u.c<<'\\n';
        }
    }
    if(env_int("MODEL_ONLY"))return 0;
'''
sub(needle,extra+'\n'+needle)
(root/'research.cpp').write_text(s)
