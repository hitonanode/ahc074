from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'mapcap.cpp').read_text()
def sub(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b)
sub('#define CAP_COUNT 1','#define CAP_COUNT 2')
sub('#define GENERIC_COUNT 38','#define GENERIC_COUNT 37')
sub('int map_cap = 63;', 'int map_cap = 62, map_cap2 = 63;')
sub('u64 pol = 0;', 'u64 pol = cap_pattern;')
sub('if (__builtin_popcountll(d) > kCutoff) continue;', 'if (__builtin_popcountll(d) > kCutoff+2) continue;')
sub('auto matching_cost = [&](const int* rel, u64 handle_mask, int cap_window)', 'auto matching_cost = [&](const int* rel, u64 handle_mask, int cap_window, int cap_window2)')
needle='''        std::array<int, 256> low{};'''
insert='''        bool cap_ok[4][4]{};
        const int cap_color=int((pol>>cap_window)&1) | (int((pol>>cap_window2)&1)<<1);
        for(int print=0;print<4;++print) {
            const int z[3]={print,(print&2)|(cap_color&1),cap_color};
            for(int a:z)for(int b:z)cap_ok[a][b]=true;
        }
'''
sub(needle,insert+needle)
sub('''            const int p = valid[i];
            const int key =''', '''            const int p = valid[i];
            const int diff=int((pairs.diff[p]>>cap_window)&1) | (int((pairs.diff[p]>>cap_window2)&1)<<1);
            const int dist144=full144[p]-144*__builtin_popcount(unsigned(diff));
            if(dist144>26*144)continue;
            const int a=int((pairs.au[p]>>cap_window)&1) | (int((pairs.au[p]>>cap_window2)&1)<<1);
            if(!cap_ok[a][a^diff])continue;
            const int key =''')
sub('+ full144[p] - 144 * int((pairs.diff[p] >> cap_window) & 1);', '+ dist144;')
sub('for (u64 q = hm | (1ULL << map_cap); q;', 'for (u64 q = hm | (1ULL << map_cap) | (1ULL << map_cap2); q;')
sub('return mv.swindow && mv.ib==63 ? mv.a : map_cap;', 'return mv.swindow && mv.ib==62 ? mv.a : map_cap;')
sub('    auto handles_after =', '    auto cap_after2 = [&](const Move& mv) {return mv.swindow && mv.ib==63 ? mv.a : map_cap2;};\n    auto handles_after =')
sub('mv.swindow && mv.ib!=63 ?', 'mv.swindow && mv.ib<62 ?')
sub('matching_cost(nrel.data(), handles_after(mv), cap_after(mv))', 'matching_cost(nrel.data(), handles_after(mv), cap_after(mv), cap_after2(mv))')
sub('matching_cost(pairs.rel.data(), hm, map_cap)', 'matching_cost(pairs.rel.data(), hm, map_cap, map_cap2)')
sub('cap_map_moves += mv.ib==63;', 'cap_map_moves += mv.ib>=62;')
sub('            map_cap = cap_after(mv);', '            map_cap = cap_after(mv);\n            map_cap2 = cap_after2(mv);')
sub('    map_cap = order[63];\n    hm = ~(1ULL << map_cap);', '    map_cap = order[62]; map_cap2=order[63];\n    hm = ~((1ULL << map_cap)|(1ULL << map_cap2));')
sub('    stats.gobj_after = cur;', '''    cap_pattern=(((pol>>order[62])&1) | (((pol>>order[63])&1)<<1))<<62;
    init_cap_table();
    std::cerr<<"map_cap_top = "<<permutation[order[62]]<<"\\nmap_cap_color = "<<cap_code(cap_pattern)<<'\\n';
    stats.gobj_after = cur;''')
(r/'mapcap2.cpp').write_text(s)
