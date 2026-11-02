from pathlib import Path
r=Path(__file__).resolve().parent
(r/'work').mkdir(exist_ok=True)
s=(r/'research.cpp').read_text()
method=r'''
// Choose both cap coordinates, their order and colors with the generic
// assignment held fixed. Enumerate all non-generic coordinates; charge the
// exact uniform generic cost and all handle differences in a 72-pair matching.
void select_caps(std::vector<u64>& A, const Comparator& comp, std::vector<int>& permutation) {
    struct Edge { int a,b,gc,dist; u64 d; };
    struct Weighted { int cost,edge; bool operator<(const Weighted& o)const {return cost!=o.cost?cost<o.cost:edge<o.edge;} };
    const int G=comp.G,need=256-(192-comp.M-kCaps);
    std::vector<Edge> edges;
    for(int a=0;a<P;++a)for(int b=a+1;b<P;++b) {
        const u64 d=A[a]^A[b];const int dist=__builtin_popcountll(d);
        if(dist>26+kCapWidth || !comp.compatible(A[a],A[b]))continue;
        auto reach=comp.closure(A[a],d);u64 rr=0;
        for(int t=0;t<6;++t)rr|=u64(reach[t])<<(8*t);
        edges.push_back({a,b,PosetSums::get().both_of(rr),dist,d});
    }
    const auto old=A;
    long long best=1LL<<60,initial=0;
    int bx=62,by=63,bc=CAP_COLORS,tried=0;
    std::vector<Weighted> work;work.reserve(edges.size());
    for(int x=G;x<64;++x)for(int y=G;y<64;++y)if(x!=y)for(int color=0;color<4;++color) {
        // Each projection has at most four prints and three insertion depths.
        bool ok[4][4]{};
        for(int p=0;p<4;++p) {
            int z[3]={p,(p&2)|(color&1),color};
            for(int a:z)for(int b:z)ok[a][b]=true;
        }
        const u64 cm=(1ULL<<x)|(1ULL<<y),hm=~(low_bits(G)|cm);
        work.clear();
        for(int i=0;i<int(edges.size());++i) {
            const auto& e=edges[i];const int da=e.dist-__builtin_popcountll(e.d&cm);
            if(da>26)continue;
            const int a=((old[e.a]>>x)&1)|(((old[e.a]>>y)&1)<<1);
            const int b=((old[e.b]>>x)&1)|(((old[e.b]>>y)&1)<<1);
            if(!ok[a][b])continue;
            work.push_back({1800*__builtin_popcountll(e.d&hm)+5*e.gc+144*da,i});
        }
        std::sort(work.begin(),work.end());
        bool used[P]{};int matched=0;long long cost=0;
        for(auto w:work) {
            const auto& e=edges[w.edge];if(used[e.a]||used[e.b])continue;
            used[e.a]=used[e.b]=true;cost+=w.cost;
            if(++matched==need)break;
        }
        cost+=1LL*(need-matched)*need*36000;
        if(x==62&&y==63&&color==CAP_COLORS)initial=cost;
        if(cost<best){best=cost;bx=x;by=y;bc=color;}
        ++tried;
    }
    std::array<int,64> order{};std::iota(order.begin(),order.end(),0);
    std::swap(order[62],order[bx]);
    int yidx=0;while(order[yidx]!=by)++yidx;
    std::swap(order[63],order[yidx]);
    const auto oldperm=permutation;
    for(int j=0;j<64;++j)permutation[j]=oldperm[order[j]];
    for(int a=0;a<P;++a) {
        A[a]=0;
        for(int j=0;j<64;++j)A[a]|=((old[a]>>order[j])&1)<<j;
    }
    cap_pattern=u64(bc)<<62;init_cap_table();
    std::cerr<<"cap_select_tried = "<<tried<<"\ncap_select_gain = "<<double(initial-best)/(need*3600)
             <<"\ngobj_selected = "<<double(best)/(need*3600)<<"\ncap_color = "<<bc
             <<"\ncap_top_window = "<<permutation[62]<<"\ncap_bottom_window = "<<permutation[63]<<'\n';
}
'''
needle='// kBitLanes[v][i]:'
idx=s.index(needle);s=s[:idx]+method+'\n'+s[idx:]
s=s.replace('        comp.rebuild();\n        des =', '        comp.rebuild();\n        select_caps(A,comp,permutation);\n        des =')
# Fixed 2 caps, G37 for the first screening.
s=s.replace('#define CAP_COUNT 1','#define CAP_COUNT 2').replace('#define GENERIC_COUNT 38','#define GENERIC_COUNT 37')
(r/'select.cpp').write_text(s)
