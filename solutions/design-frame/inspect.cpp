// Saved designs only: no interactive solution or tester is run.
#define main inherited_main
#include "main.cpp"
#undef main
#include <bit>
#include <iomanip>
#include <set>

namespace frame {
u64 parse(const std::string& s) {
    u64 x=0;
    for(int j=0;j<int(s.size());++j) if(s[j]=='1') x|=1ULL<<j;
    return x;
}
using Pair=std::pair<int,int>;
struct Edge { int a,b; u64 diff; double gc; };
struct Matching { double value=0; std::vector<Pair> pairs; };
Matching match(const std::vector<Edge>& edges,u64 hm,int cap,double weight,bool close=true) {
    std::vector<std::pair<int,Pair>> costs;
    for(const auto& e:edges) {
        const u64 d=e.diff&~(1ULL<<cap);
        if(close && std::popcount(d)>26) continue;
        const int key=int(std::lround(3600*weight))*std::popcount(d&hm)
            +5*int(std::lround(1440*e.gc))+144*std::popcount(d);
        costs.push_back({key,{e.a,e.b}});
    }
    std::sort(costs.begin(),costs.end());
    std::array<bool,P> used{};
    Matching out;
    for(auto [v,p]:costs) if(!used[p.first]&&!used[p.second]) {
        used[p.first]=used[p.second]=true;
        out.pairs.push_back(p); out.value+=v;
        if(out.pairs.size()==71) break;
    }
    out.value=out.value/(71*3600)+10*(71-int(out.pairs.size()));
    return out;
}
int overlap(std::vector<Pair> a,std::vector<Pair> b) {
    std::sort(a.begin(),a.end());std::sort(b.begin(),b.end());
    int n=0;
    for(auto p:a)n+=std::binary_search(b.begin(),b.end(),p);
    return n;
}
int run(int argc,char**argv) {
    if(argc<3)return 2;
    std::ifstream in(argv[1]);int n,k,p,r;in>>n>>k>>p>>r;
    std::vector<u64> original(P);std::string s;
    for(auto& a:original){in>>s;a=parse(s);}
    setenv("DESIGN_LOAD_DIR",argv[2],1);
    DesignStore ds(original);
    std::ostringstream discard;
    auto old=std::cerr.rdbuf(discard.rdbuf());auto st=ds.load(original);std::cerr.rdbuf(old);
    if(st.emergency || st.G!=38 || st.M!=6)return 3;
    auto sol=make_solver(st);auto& comp=sol.comparator;
    const u64 gm=low_bits(st.G),hm=kActiveWindows&~gm;
    std::vector<Edge> edges;
    for(int a=0;a<P;++a)for(int b=a+1;b<P;++b) {
        const auto reach=comp.closure(st.A[a],st.A[a]^st.A[b]);u64 rel=0;
        for(int j=0;j<6;++j)rel|=u64(reach[j])<<(8*j);
        if(rel&kDiagonal)continue;
        edges.push_back({a,b,st.A[a]^st.A[b],PosetSums::get().both_of(rel)/1440.0});
    }
    const auto map=match(edges,hm,63,0.5);
    auto active=st.A;for(auto& a:active)a&=kActiveWindows;
    Design initial(active,6,st.G);
    auto estimate=[&](u64 a,u64 b){auto rr=comp.closure(a,a^b);u64 rel=0;for(int j=0;j<6;++j)rel|=u64(rr[j])<<(8*j);return PosetSums::get().both_of(rel)/1440.0;};
    if(!initial.initialize([&](u64 a,u64 b){return comp.compatible(a,b);},estimate,[]{return false;}))return 5;
    Matching init;
    for(auto u:initial.unit)if(u.b>=0)init.pairs.push_back(std::minmax(u.a,u.b));
    std::vector<Pair> final;
    std::vector<std::vector<int>> served(K);
    for(int a=0;a<P;++a)served[st.ded[a]].push_back(a);
    double finalg=0,allhd=0,shallowhd=0,deep=0,col=0;
    int beyond=0;
    for(int x=7;x<K;++x)if(served[x].size()==2) {
        const int a=served[x][0],b=served[x][1],c=st.columns[x];final.push_back({a,b});
        const u64 diff=st.A[a]^st.A[b];
        u64 prefix=0;for(int j=0;j<=c;++j)prefix|=1ULL<<st.handle[j];
        allhd+=std::popcount(diff&hm);shallowhd+=std::popcount(diff&prefix);deep+=st.H-1-c;col+=c;
        beyond+=std::popcount(diff&kActiveWindows)>26;
        auto it=std::find_if(edges.begin(),edges.end(),[&](auto e){return e.a==a&&e.b==b;});
        if(it==edges.end())return 4;
        finalg+=0.5*std::popcount(diff&hm)+2*it->gc+0.04*std::popcount(diff&kActiveWindows);
    }
    int cap=63;auto best=map;
    std::vector<double> cap_values;
    for(int j=st.G;j<64;++j) {
        auto cur=match(edges,~gm&~(1ULL<<j),j,0.5);
        cap_values.push_back(cur.value);
        if(cur.value<best.value-1e-9){best=cur;cap=j;}
    }
    std::cout<<std::setprecision(12)<<"{\"map_gobj\":"<<map.value<<",\"final_gobj\":"<<finalg/71
             <<",\"map_init_overlap\":"<<overlap(map.pairs,init.pairs)<<",\"map_final_overlap\":"<<overlap(map.pairs,final)
             <<",\"init_final_overlap\":"<<overlap(init.pairs,final)<<",\"final_beyond26\":"<<beyond
             <<",\"pair_handle_diff\":"<<allhd/71<<",\"pair_shallow_diff\":"<<shallowhd/71
             <<",\"pair_deep_holes\":"<<deep/71<<",\"pair_column\":"<<col/71
             <<",\"cap_gain\":"<<best.value-map.value<<",\"cap_changed\":"<<(cap!=63)
             <<",\"cap_original\":"<<st.permutation[cap]<<",\"cap_overlap\":"<<overlap(map.pairs,best.pairs)
             <<",\"cap_values\":[";
    for(size_t i=0;i<cap_values.size();++i)std::cout<<(i?",":"")<<cap_values[i];
    std::cout<<"],\"moves\":[";
    // Optional enumeration of single-window relabels and generic/handle swaps.
    // Use the actual initial/final pair sets, never redraw them to hide losses.
    if(argc>=4 && std::stoi(argv[3])) {
        for(int phase=0;phase<2;++phase) {
            const auto& pairs=phase?final:init.pairs;
            std::array<long long,72> flips{},transfers{},swaps{};
            Design model=initial;
            if(phase) {
                model.unit.clear();model.handle=st.handle;
                for(int x=7;x<K;++x) {
                    model.unit.push_back({served[x][0],served[x].size()==2?served[x][1]:-1,st.columns[x]});
                }
                for(int u=0;u<P;++u)model.hb[u]=sol.handle_bits(model.A[u]);
                model.rebuild();
            }
            model.refresh_reset();
            int safe=0,improved=0;double best_delta=0;
            // Joint moves are evaluated with existing pairs and columns held
            // fixed. Invalid own-handle colors or monochrome columns are rejected.
            auto full_cost=[&](const Comparator& c,int a,int b) {
                Design next=model;
                if(b>=0) for(int u=0;u<P;++u) {
                    const u64 flip=((next.A[u]>>a)^(next.A[u]>>b))&1;
                    next.A[u]^=(flip<<a)|(flip<<b);next.hb[u]=0;
                    for(int j=0;j<next.H;++j)next.hb[u]|=((next.A[u]>>next.handle[j])&1)<<j;
                }
                for(const auto& u:next.unit) {
                    if(!next.valid(u,u.c))return;
                    if(u.b<0)continue;
                    const auto rr=c.closure(next.A[u.a],next.A[u.a]^next.A[u.b]);u64 rel=0;
                    for(int j=0;j<6;++j)rel|=u64(rr[j])<<(8*j);
                    if(rel&kDiagonal)return;
                    next.gcost[u.a][u.b]=next.gcost[u.b][u.a]=PosetSums::get().both_of(rel)/1440.0;
                }
                next.rebuild();
                for(int j=0;j<next.H;++j)if(!next.n1[j]||next.n1[j]==next.nc[j])return;
                ++safe;const double delta=(next.cur-model.cur)/P;
                improved+=delta<-1e-9;best_delta=std::min(best_delta,delta);
            };
            auto losses=[&](const Comparator& c,int a,int b){
                int lost=0;
                for(auto [u,v]:pairs) {
                    u64 au=st.A[u],av=st.A[v];
                    if(b>=0) {
                        const u64 xu=((au>>a)^(au>>b))&1,xv=((av>>a)^(av>>b))&1;
                        au^=(xu<<a)|(xu<<b);av^=(xv<<a)|(xv<<b);
                    }
                    lost+=!c.compatible(au,av);
                }
                return lost;
            };
            for(int j=0;j<st.G;++j) {
                auto c=comp;c.polarity[j]^=1;int lost=losses(c,j,-1);++flips[lost];
                if(!lost)full_cost(c,j,-1);
                int multiplicity=0;for(auto edge:comp.edge)multiplicity+=edge==comp.edge[j];
                for(int a=0;a<6;++a)for(int b=a+1;b<6;++b)for(int pol=0;pol<2;++pol) {
                    if(multiplicity<=1)continue;
                    if(comp.edge[j]==Pair{a,b})continue;
                    c.edge[j]={a,b};c.polarity[j]=pol;lost=losses(c,j,-1);++transfers[lost];
                    if(!lost)full_cost(c,j,-1);
                }
                c=comp;
                for(int h=st.G;h<63;++h)for(int pol=0;pol<2;++pol) {
                    c.polarity[j]=pol;lost=losses(c,j,h);++swaps[lost];
                    if(!lost)full_cost(c,j,h);
                }
            }
            std::cout<<(phase?",":"")<<"{\"phase\":"<<phase<<",\"safe\":"<<safe
                     <<",\"improved\":"<<improved<<",\"best_delta\":"<<best_delta;
            auto emit=[&](const char* name,const auto& v){std::cout<<",\""<<name<<"\":[";for(int i=0;i<72;++i)std::cout<<(i?",":"")<<v[i];std::cout<<']';};
            emit("flip",flips);emit("transfer",transfers);emit("swap",swaps);std::cout<<'}';
        }
    }
    std::cout<<"]}\n";return 0;
}
}
int main(int argc,char**argv){return frame::run(argc,argv);}
