WindowStats assign_windows(std::vector<u64>& A,int m,int g,
    std::vector<std::pair<int,int>>& edges,std::vector<int>& polarity,
    std::vector<int>& permutation,double seconds,int fixed_iters,int climb_steps,double climb_seconds) {
    assert(m==7&&g>=21&&g<64);
    auto& costs=Poset7Costs::get();
    const double start=elapsed_sec();
    constexpr int need=72;
    const bool sparse = env_int("SPARSE_WINDOWS") > 0;
    XorShift rng{0x71eb2566be932e31ULL};
    std::vector<std::pair<int,int>> ep;
    int index[7][7];std::memset(index,-1,sizeof(index));
    for(int a=0;a<7;a++)for(int b=a+1;b<7;b++)index[a][b]=index[b][a]=ep.size(),ep.push_back({a,b});
    std::array<u64,21> masks{},forward{},reverse{};
    std::array<int,64> which{},order{};which.fill(-1);std::iota(order.begin(),order.end(),0);
    std::array<int,21> counts{};
    u64 pol=0,hm=kActiveWindows & ~low_bits(g);
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
            int key=25200*__builtin_popcountll(x.d&handles)+10*(c-1)+2016*x.dist;
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
    long long full=0,escapes=0;unsigned generation=1;
    std::vector<unsigned> seen(1<<20);
    int no_accept=0;
    double escape_score=1e100;auto escape_masks=masks;auto escape_order=order;u64 escape_pol=pol;
    auto restore_state=[&](const auto& mm,const auto& oo,u64 pp) {
        masks=mm;order=oo;pol=pp;hm=0;which.fill(-1);
        for(int j=g;j<63;j++)hm|=1ULL<<order[j];
        for(int e=0;e<21;e++) {
            counts[e]=__builtin_popcountll(masks[e]);
            for(u64 s=masks[e];s;s&=s-1)which[__builtin_ctzll(s)]=e;
        }
        for(auto& p:pairs)p.r=relation(p.a,p.d),p.rel=costs.cost(p.r);
        current=matching(hm,false,selected);generation++;no_accept=0;escape_score=1e100;
    };
    struct Option {int ib,edge,color,loss;};
    struct Options {unsigned epoch=0;std::vector<Option>rows;};
    std::array<std::array<Options,3>,64>options;
    auto stage=[&](double duration,int iterations,bool climb) {
        const double st=elapsed_sec();double now=st;
        for(int it=0;;it++) {
            if((it&31)==0) {
                now=elapsed_sec();
                if(iterations>0?it>=iterations:now-st>=duration)break;
            }
            if(climb)stats.climb_steps++;else stats.iterations++;
            no_accept++;
            if(no_accept>=(climb?512:256)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                escapes++;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
            int ia=rng.mod(g),ib=rng.mod(g),a=order[ia],b=order[ib];
            bool swap_window=rng.real()<0.6;
            if(swap_window)ib=g+rng.mod(63-g),b=order[ib];
            int kind=rng.mod(10),ea=which[a],eb=swap_window?ea:which[b],transfer=-1;
            bool cross=swap_window && rng.mod(16)==0;
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
                if(swap_window){which[a]=-1;which[b]=eb;std::swap(order[ia],order[ib]);if(ea!=eb){counts[ea]--;counts[eb]++;}}
                else if(kind>=3&&kind<8)std::swap(which[a],which[b]);
                else if(transfer>=0)counts[ea]--,counts[eb]++,which[a]=eb;
                generation++;no_accept=0;escape_score=1e100;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            } else {
                masks[ea]=olda;masks[eb]=oldb;pol=oldpol;
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
    std::cerr<<"map_escapes = "<<escapes<<"\nmap_full_evaluations = "<<full<<"\nposet7_cache_misses = "<<costs.misses<<'\n';
    return stats;
}
