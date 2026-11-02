from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'model.cpp').read_text();old=(p/'prior7.cpp').read_text()
# Reuse the independently validated 2045 exact seven-element poset costs.
x=old.index('u64 canonical7(');y=old.index('// The seven-sheet graph',x)
extra=old[x:y]
x=old.index('WindowStats assign_windows(',y);y=old.index('#define AVX2_TARGET',x)
a7=old[x:y]
a7=a7.replace('constexpr int need=71;','constexpr int need=72;\n    const bool sparse = env_int("SPARSE_WINDOWS") > 0;')
a7=a7.replace('hm=~low_bits(g)','hm=kActiveWindows & ~low_bits(g)')
a7=a7.replace('j<64;j++)hm','j<63;j++)hm').replace('rng.mod(64-g)','rng.mod(63-g)')
a7=a7.replace('32760*__builtin_popcountll','25200*__builtin_popcountll')
a7=a7.replace('std::array<unsigned,32768> seen{};','std::vector<unsigned> seen(1<<20);')
a7=a7.replace('(climb?2048:1024)','(climb?512:256)')
a7=a7.replace('''            int memo=0;
            if(swap_window)memo=a*64+b;
            else if(kind<3)memo=4096+a;
            else if(kind<8) {
                if(ea==eb)continue;memo=8192+std::min(a,b)*64+std::max(a,b);
            } else {
                if(counts[ea]<2)continue;eb=rng.mod(21);if(ea==eb)continue;
                transfer=eb;memo=16384+a*32+eb;
            }
            if(seen[memo]==generation)continue;seen[memo]=generation;
            const u64 olda=masks[ea],oldb=masks[eb],oldpol=pol;
            if(swap_window) {
                masks[ea]^=(1ULL<<a)|(1ULL<<b);
                pol=(pol&~(1ULL<<b))|(((oldpol>>a)&1)<<b);
            } else if(kind<3)pol^=1ULL<<a;
            else if(kind<8)masks[ea]^=(1ULL<<a)|(1ULL<<b),masks[eb]^=(1ULL<<a)|(1ULL<<b);
            else masks[ea]^=1ULL<<a,masks[eb]|=1ULL<<a;
''','''            bool cross=swap_window && rng.mod(16)==0;
            int newcolor=int(pol>>a&1), memo=0;
            auto can_remove=[&](int e){return counts[e]>1 || (sparse && ep[e].second==6);};
            auto same_kind=[&](int x,int y){return !sparse || ((ep[x].second==6)==(ep[y].second==6));};
            if(swap_window || kind>=8) {
                int typ=swap_window?(cross?2:0):1;
                auto& cache=options[a][typ];
                if(cache.epoch!=generation) {
                    cache.epoch=generation;cache.rows.clear();
                    if(typ==0 || can_remove(ea)) {
                        for(int jj=(swap_window?g:ia);jj<(swap_window?63:ia+1);jj++) {
                            int w=order[jj];
                            for(int ee=0;ee<21;ee++) {
                                if((typ==0&&ee!=ea)||(typ!=0&&(ee==ea||!same_kind(ea,ee))))continue;
                                for(int color=0;color<2;color++) {
                                    u64 ma=masks[ea]&~(1ULL<<a), mb=masks[ee];
                                    if(ee==ea)ma|=1ULL<<w,mb=ma;else mb|=1ULL<<w;
                                    u64 pp=(pol&~(1ULL<<w))|(u64(color)<<w);
                                    u64 erase=forward[ea]|reverse[ea]|forward[ee]|reverse[ee];
                                    int lost=0;
                                    for(int z:selected) {
                                        const auto& x=pairs[z];u64 rr=x.r&~erase,zz=x.a^pp;
                                        u64 da=x.d&ma,db=x.d&mb;
                                        if(da&~zz)rr|=forward[ea];if(da&zz)rr|=reverse[ea];
                                        if(db&~zz)rr|=forward[ee];if(db&zz)rr|=reverse[ee];
                                        if((closure8(rr,7)&kDiagonal)&&++lost>=3)break;
                                    }
                                    if(lost<3)cache.rows.push_back({jj,ee,color,lost});
                                }
                            }
                        }
                    }
                }
                if(cache.rows.empty())continue;
                int total=0;for(auto&o:cache.rows)total+=1<<(2-o.loss);
                int pick=rng.mod(total),ix=0;
                while(pick>=(1<<(2-cache.rows[ix].loss)))pick-=1<<(2-cache.rows[ix++].loss);
                auto opt=cache.rows[ix];cache.rows[ix]=cache.rows.back();cache.rows.pop_back();
                ib=opt.ib;b=order[ib];eb=opt.edge;newcolor=opt.color;
                if(!swap_window)transfer=eb;
                memo=16384+2*(21*(a*64+b)+eb)+newcolor;
            } else if(kind<3)memo=8192+a;
            else {if(ea==eb)continue;memo=8256+std::min(a,b)*64+std::max(a,b);}
            if(seen[memo]==generation)continue;seen[memo]=generation;
            const u64 olda=masks[ea],oldb=masks[eb],oldpol=pol;
            if(swap_window) {
                masks[ea]&=~(1ULL<<a);masks[eb]|=1ULL<<b;
                pol=(pol&~(1ULL<<b))|(u64(newcolor)<<b);
            } else if(kind<3)pol^=1ULL<<a;
            else if(kind<8)masks[ea]^=(1ULL<<a)|(1ULL<<b),masks[eb]^=(1ULL<<a)|(1ULL<<b);
            else {masks[ea]^=1ULL<<a;masks[eb]|=1ULL<<a;pol=(pol&~(1ULL<<a))|(u64(newcolor)<<a);}
''')
a7=a7.replace('''    auto stage=[&](double duration,int iterations,bool climb) {''','''    struct Option {int ib,edge,color,loss;};
    struct Options {unsigned epoch=0;std::vector<Option>rows;};
    std::array<std::array<Options,3>,64>options;
    auto stage=[&](double duration,int iterations,bool climb) {''')
a7=a7.replace('if(swap_window)which[a]=-1,which[b]=ea,std::swap(order[ia],order[ib]);','''if(swap_window){which[a]=-1;which[b]=eb;std::swap(order[ia],order[ib]);if(ea!=eb){counts[ea]--;counts[eb]++;}}''')
(p/'assignment7.inc').write_text(a7)
# Latest six-sheet assignment remains the sparse design initializer, with all
# current compound moves. Seven-sheet search has the same move families and
# explicit loss-screened candidate enumeration, on an unpacked 7x7 relation.
s=s.replace('WindowStats assign_windows(', 'WindowStats assign_windows6(')
a=s.index('// kBitLanes[v][i]')
s=s[:a]+extra+'\n'+a7+'\n'+s[a:]
s=s.replace('kCapPaper = 6','kCapPaper = 7')
s=s.replace('int M = 6, G = 38;  // as6-cap38: 38 generic windows','int M = 7, G = 38;  // Seven generic sheets plus the fixed cap.')
a='''        comp.init(M, G, rng);
        if (attempt < 2) {'''
b='''        if (int sparse=env_int("SPARSE_WINDOWS"); sparse>0) {
            comp.init(6,G,rng);
            auto initial=assign_windows6(A,6,G,comp.edge,comp.polarity,permutation,1e9,400000,100000,0);
            std::array<std::array<int,6>,6> counts{};
            for(auto[x,y]:comp.edge)++counts[x][y];
            XorShift rr{0xe123faf611ULL};
            for(int t=0;t<sparse;) {
                int j=rr.mod(G);auto[x,y]=comp.edge[j];
                if(y==6 || counts[x][y]<=1)continue;
                --counts[x][y];int keep=rr.mod(2)?x:y;comp.edge[j]={keep,6};++t;
            }
            comp.M=7;comp.rebuild();
            std::cerr << "sparse_initializer_gobj = " << initial.gobj_after << '\\n';
        } else comp.init(M,G,rng);
        if (attempt < 2) {'''
assert a in s;s=s.replace(a,b)
s=s.replace('return PosetSums::get().both_of(r) / 1440.0;', 'return (Poset7Costs::get().cost(r) - 1) / 10080.0;')
# Legal graph and fast relative distances from the prior validated seven-sheet work.
a=s.index('struct Comparator {');b=s.index('// Closure of a relation bit matrix',a)
x=old.index('struct Comparator {');y=old.index('// Seven-sheet exact decoder costs.',x)
comp=old[x:y]
# The old 7-sheet memo had a 6-bit row encoding; avoid collisions in research use.
comp=comp.replace('<< (6 * a)','<< (8 * a)')
comp=comp.replace('''        if (M == 7) {
            unsigned code''','''        if (M == 7 && !complete) return dist[a * perms.size() + b];
        if (M == 7) {
            unsigned code''')
comp=comp.replace('''                for (int pos = 0; pos < 6; pos++) for (int d = 0; d < 7; d++) if (pos != d) {''','''                unsigned visible=0;u64 covered=0;
                for(int pos=0;pos<7;pos++){int k=perms[a][pos];if(opq[k]&~covered)visible|=1U<<pos;covered|=opq[k];}
                for (int pos = 0; pos < 6; pos++) for (int d = 0; d < 7; d++) if (pos != d && (visible>>pos&1)) {''')
comp=comp.replace('''            std::vector<unsigned char> ds(n, 255);''','''            if(!complete){
                dist.assign(n*n,255);std::vector<int>q(n);
                for(int source=0;source<n;source++){
                    uint8_t* ds=dist.data()+source*n;int head=0,tail=0;ds[source]=0;q[tail++]=source;
                    while(head<tail){int x=q[head++];for(int y:next[x])if(y>=0&&ds[y]==255)ds[y]=ds[x]+1,q[tail++]=y;}
                    assert(tail==n);
                }
                return;
            }
            std::vector<unsigned char> ds(n, 255);''',1)
comp=comp.replace('''        auto reach = closure(target, holes);
        u64 key = 0;''','''        auto reach = closure(target, holes);
        u64 key = 0;''')
needle='''        const int n = perms.size();
        std::vector<int> sat;
        for (int t = 0; t < n; t++) {'''
# Exact means of sparse patterns use legal reverse BFS, never complete-graph costs.
comp=comp.replace(needle,'''        const int n = perms.size();
        if(M==7){
            auto sat=satisfying(target,holes);if(sat.empty())return 1000;
            std::vector<unsigned char>ds(n,255);std::vector<int>q(n);int head=0,tail=0;
            for(int s:sat)ds[s]=0,q[tail++]=s;
            while(head<tail){int x=q[head++];for(int y:previous7[x])if(ds[y]==255)ds[y]=ds[x]+1,q[tail++]=y;}
            assert(tail==n);double sum=0;for(int d:ds)sum+=d;
            double mean=sum/n;memo.insert(it,{key,mean});return mean;
        }
        std::vector<int> sat;
        for (int t = 0; t < n; t++) {''')
comp=comp.replace('''        if (!complete || int(current.size()) != M) return {{-1, -1}};''','''        if (int(current.size()) != M) return {{-1,-1}};
        if(!complete){auto sat=satisfying(target,holes);int start=order_index(current),best=-1,bd=255;for(int s:sat)if(distance(start,s)<bd)bd=distance(start,s),best=s;return best<0?std::vector<std::pair<int,int>>{{-1,-1}}:path(start,best);}''')
s=s[:a]+comp+s[b:]
s=s.replace('''        auto estimate = [&](u64 a, u64 b) {
            const auto reach''','''        auto estimate = [&](u64 a, u64 b) {
            if (!comp.complete) return 0.5*(comp.mean_moves(a,a^b)+comp.mean_moves(b,a^b));
            const auto reach''')
# Use the current helper machinery for seven sheets too: model and simulation
# include its benefit; its much larger time cost is measured, not hidden.
s=s.replace('static constexpr int GM = 6;', 'static constexpr int GM = 7;')
s=s.replace('if (M == Interleave::GM && comp.complete)', 'if (M == Interleave::GM)')
a=s.index('    void init_lookahead() {');b=s.index('    // Adaptive columns:',a)
x=old.index('    void init_lookahead() {');y=old.index('    // Adaptive columns:',x)
s=s[:a]+old[x:y]+s[b:]
# Explicit measurement error instead of changing G or switching algorithms.
s=s.replace('''        if (attempt >= 2 || (!untimed && elapsed_sec() > kInitGiveUp)) return emergency_design(originalA, R);
        G = attempt == 0 ? 32 : 28;''','''        std::cerr << "design_failed = 1\\n";return 2;''')
(p/'seven.cpp').write_text(s)
