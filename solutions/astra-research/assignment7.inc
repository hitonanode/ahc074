// Seven-sheet exact decoder costs. The embedded table is generated offline.
u64 closure8(u64 r, int m) {
    for(int k=0;k<m;k++)r|=((r>>k)&0x0101010101010101ULL)*((r>>(8*k))&255);
    return r;
}
constexpr u64 kDiagonal=0x8040201008040201ULL;
u64 transpose8(u64 r) {
    u64 t=(r^(r>>7))&0x00AA00AA00AA00AAULL;r^=t^(t<<7);
    t=(r^(r>>14))&0x0000CCCC0000CCCCULL;r^=t^(t<<14);
    t=(r^(r>>28))&0x00000000F0F0F0F0ULL;r^=t^(t<<28);return r;
}
struct PosetClass {u64 relation;int sum;};
// @CANONICAL7@
// @POSET7_TABLE@

struct Poset7Costs {
    static constexpr unsigned CS=1U<<19;
    std::vector<u64> keys;
    std::vector<int> values;
    std::array<int,2045> both{};
    long long misses=0;
    static unsigned hash(u64 r) {
        r^=r>>27;r*=0x3c79ac492ba7b653ULL;r^=r>>33;
        return unsigned(r)&(CS-1);
    }
    static int find(u64 c) {
        auto it=std::lower_bound(std::begin(kPoset7Classes),std::end(kPoset7Classes),c,
            [](const PosetClass& x,u64 r){return x.relation<r;});
        assert(it!=std::end(kPoset7Classes)&&it->relation==c);
        return int(it-std::begin(kPoset7Classes));
    }
    Poset7Costs():keys(CS,~0ULL),values(CS) {
        for(int i=0;i<2045;i++)both[i]=kPoset7Classes[i].sum+
            kPoset7Classes[find(canonical7(transpose8(kPoset7Classes[i].relation)))].sum;
    }
    // 0 for impossible, otherwise 1 + sum of the distances for both target colors.
    int cost(u64 raw) {
        unsigned h=hash(raw);
        if(keys[h]==raw)return values[h];
        int value=0;
        if(!(raw&transpose8(raw))) {
            u64 closed=closure8(raw,7);
            if(!(closed&kDiagonal)) {
                misses++;
                value=1+both[find(canonical7(closed))];
            }
        }
        keys[h]=raw;values[h]=value;return value;
    }
    static Poset7Costs& get(){static Poset7Costs p;return p;}
};

// The seven-sheet graph has 21 unordered comparisons, exceeding the 16-bit
// direction encoding of astra-search4. Keep the exact 8-by-8 relation matrix.
struct WindowStats {
    int iterations=0;double score=0,gobj_before=0,gobj_after=0;int climb_steps=0;
};
WindowStats assign_windows(std::vector<u64>& A,int m,int g,
    std::vector<std::pair<int,int>>& edges,std::vector<int>& polarity,
    std::vector<int>& permutation,double seconds,int fixed_iters,int climb_steps,double climb_seconds) {
    assert(m==7&&g>=21&&g<64);
    auto& costs=Poset7Costs::get();
    const double start=elapsed_sec();
    constexpr int need=71;
    XorShift rng{0x71eb2566be932e31ULL};
    std::vector<std::pair<int,int>> ep;
    int index[7][7];std::memset(index,-1,sizeof(index));
    for(int a=0;a<7;a++)for(int b=a+1;b<7;b++)index[a][b]=index[b][a]=ep.size(),ep.push_back({a,b});
    std::array<u64,21> masks{},forward{},reverse{};
    std::array<int,64> which{},order{};which.fill(-1);std::iota(order.begin(),order.end(),0);
    std::array<int,21> counts{};
    u64 pol=0,hm=~low_bits(g);
    for(int e=0;e<21;e++)forward[e]=1ULL<<(8*ep[e].first+ep[e].second),reverse[e]=1ULL<<(8*ep[e].second+ep[e].first);
    for(int j=0;j<g;j++) {
        auto[a,b]=edges[j];int e=index[a][b];masks[e]|=1ULL<<j;counts[e]++;which[j]=e;
        if(polarity[j]^(a>b))pol|=1ULL<<j;
    }
    struct Pair {u64 a,d,r;int u,v,dist,rel;};
    std::vector<Pair> pairs;
    auto relation=[&](u64 a,u64 d) {
        u64 z=a^pol,r=0;
        for(int e=0;e<21;e++){u64 x=d&masks[e];if(x&~z)r|=forward[e];if(x&z)r|=reverse[e];}
        return r;
    };
    for(int u=0;u<256;u++)for(int v=u+1;v<256;v++) {
        u64 d=A[u]^A[v];int hd=__builtin_popcountll(d);
        if(hd>26)continue;
        u64 r=relation(A[u],d);pairs.push_back({A[u],d,r,u,v,hd,costs.cost(r)});
    }
    const int np=pairs.size();
    std::vector<u64> nr(np);std::vector<int> nc(np),selected,newselected;
    std::vector<std::pair<int,int>> sorted;sorted.reserve(np);
    auto matching=[&](u64 handles,bool next,std::vector<int>& matching)->double {
        sorted.clear();
        for(int p=0;p<np;p++) {
            int c=next?nc[p]:pairs[p].rel;if(!c)continue;
            const auto& x=pairs[p];
            // 50400 times (0.65 handle differences + both legal means + 0.04 all differences).
            int key=32760*__builtin_popcountll(x.d&handles)+10*(c-1)+2016*x.dist;
            sorted.emplace_back(key,p);
        }
        std::sort(sorted.begin(),sorted.end());
        std::array<unsigned char,256> used{};matching.clear();long long sum=0;
        for(auto[key,p]:sorted) {
            const auto& x=pairs[p];if(used[x.u]||used[x.v])continue;
            used[x.u]=used[x.v]=1;matching.push_back(p);sum+=key;
            if(int(matching.size())==need)break;
        }
        return double(sum)/(50400*need)+10.0*(need-int(matching.size()));
    };
    double current=matching(hm,false,selected),best=current;
    auto best_masks=masks;auto best_order=order;u64 best_pol=pol;
    WindowStats stats;stats.gobj_before=current;
    long long full=0;unsigned generation=1;
    std::array<unsigned,32768> seen{};
    int no_accept=0;
    double escape_score=1e100;auto escape_masks=masks;auto escape_order=order;u64 escape_pol=pol;
    auto restore_state=[&](const auto& mm,const auto& oo,u64 pp) {
        masks=mm;order=oo;pol=pp;hm=0;which.fill(-1);
        for(int j=g;j<64;j++)hm|=1ULL<<order[j];
        for(int e=0;e<21;e++) {
            counts[e]=__builtin_popcountll(masks[e]);
            for(u64 s=masks[e];s;s&=s-1)which[__builtin_ctzll(s)]=e;
        }
        for(auto& p:pairs)p.r=relation(p.a,p.d),p.rel=costs.cost(p.r);
        current=matching(hm,false,selected);generation++;no_accept=0;escape_score=1e100;
    };
    auto stage=[&](double duration,int iterations,bool climb) {
        const double st=elapsed_sec();double now=st;
        for(int it=0;;it++) {
            if((it&31)==0) {
                now=elapsed_sec();
                if(iterations>0?it>=iterations:now-st>=duration)break;
            }
            if(climb)stats.climb_steps++;else stats.iterations++;
            int ia=rng.mod(g),ib=rng.mod(g),a=order[ia],b=order[ib];
            bool swap_window=rng.real()<0.6;
            if(swap_window)ib=g+rng.mod(64-g),b=order[ib];
            int kind=rng.mod(10),ea=which[a],eb=swap_window?ea:which[b],transfer=-1;
            int memo=0;
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
            u64 erase=forward[ea]|reverse[ea]|forward[eb]|reverse[eb];
            auto changed_relation=[&](const Pair& x) {
                u64 r=x.r&~erase,z=x.a^pol,da=x.d&masks[ea],db=x.d&masks[eb];
                if(da&~z)r|=forward[ea];if(da&z)r|=reverse[ea];
                if(db&~z)r|=forward[eb];if(db&z)r|=reverse[eb];return r;
            };
            int lost=0;
            for(int p:selected) {
                u64 r=changed_relation(pairs[p]);
                if(r!=pairs[p].r&&(closure8(r,7)&kDiagonal)) {
                    if(++lost>=3)break;
                }
            }
            if(lost>=3) {masks[ea]=olda;masks[eb]=oldb;pol=oldpol;continue;}
            full++;
            for(int p=0;p<np;p++) {
                nr[p]=changed_relation(pairs[p]);
                nc[p]=nr[p]==pairs[p].r?pairs[p].rel:costs.cost(nr[p]);
            }
            u64 nhm=swap_window?hm^((1ULL<<a)|(1ULL<<b)):hm;
            double next=matching(nhm,true,newselected);
            double progress=iterations>0?double(it)/iterations:(now-st)/duration;
            double temp=climb?0.0:0.05*std::pow(0.025,progress);
            bool accept=next<=current||(!climb&&rng.real()<std::exp((current-next)/temp));
            if(next<escape_score) {
                escape_score=next;escape_masks=masks;escape_pol=pol;escape_order=order;
                if(swap_window)std::swap(escape_order[ia],escape_order[ib]);
            }
            if(accept) {
                for(int p=0;p<np;p++)pairs[p].r=nr[p],pairs[p].rel=nc[p];
                hm=nhm;selected.swap(newselected);current=next;
                if(swap_window)which[a]=-1,which[b]=ea,std::swap(order[ia],order[ib]);
                else if(kind>=3&&kind<8)std::swap(which[a],which[b]);
                else if(transfer>=0)counts[ea]--,counts[eb]++,which[a]=eb;
                generation++;no_accept=0;escape_score=1e100;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            } else {
                masks[ea]=olda;masks[eb]=oldb;pol=oldpol;no_accept++;
            }
            if(no_accept>=(climb?2048:1024)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
        }
    };
    stage(std::max(0.0,seconds-(elapsed_sec()-start)),fixed_iters,false);
    restore_state(best_masks,best_order,best_pol);
    if(climb_steps>0||climb_seconds>0)stage(climb_seconds,climb_steps,true);
    masks=best_masks;order=best_order;pol=best_pol;
    for(int j=0;j<g;j++) {
        int x=order[j],e=0;while(e<21&&!(masks[e]>>x&1))e++;
        assert(e<21);edges[j]=ep[e];polarity[j]=(pol>>x)&1;
    }
    auto oldperm=permutation;
    for(int j=0;j<64;j++)permutation[j]=oldperm[order[j]];
    for(u64& a:A){u64 b=0;for(int j=0;j<64;j++)b|=((a>>order[j])&1)<<j;a=b;}
    stats.score=best;stats.gobj_after=best;
    std::cerr<<"map_full_evaluations = "<<full<<"\nposet7_cache_misses = "<<costs.misses<<'\n';
    return stats;
}
#define AVX2_TARGET __attribute__((target("avx2,popcnt")))
