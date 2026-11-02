// Read saved MODEL_ONLY dumps; no request sequence is consulted.
#include <fstream>
#include <iomanip>
#define main research_entry
#include "research.cpp"
#undef main
int main(int argc,char**argv) {
    std::cout<<std::setprecision(12);
    for(int f=1;f<argc;++f) {
        std::ifstream in(argv[f]);
        int g,c,w,col;in>>g>>c>>w>>col;
        if(!in || c!=0) return 2;
        std::array<int,64> permutation;for(auto&x:permutation)in>>x;
        Comparator cmp;cmp.M=6;cmp.G=g;cmp.edge.resize(g);cmp.polarity.resize(g);
        for(int j=0;j<g;++j)in>>cmp.edge[j].first>>cmp.edge[j].second>>cmp.polarity[j];
        cmp.rebuild();
        std::vector<u64>a(P);for(auto&x:a)in>>x;
        const int h=64-g;std::vector<int>handle(h);for(auto&x:handle)in>>x;
        std::vector<Design::Unit>units(186);for(auto&x:units)in>>x.a>>x.b>>x.c;
        struct Edge { int cost,a,b; bool operator<(const Edge&o)const{return cost!=o.cost?cost<o.cost:std::pair(a,b)<std::pair(o.a,o.b);} };
        auto gc=[&](int u,int v,u64 mask)->int {
            auto r=cmp.closure(a[u],(a[u]^a[v])&mask);u64 packed=0;
            for(int i=0;i<6;++i){if(r[i]>>i&1)return -1;packed|=u64(r[i])<<(8*i);}
            return PosetSums::get().both_of(packed);
        };
        struct Result{double match70=0,match71=0,gc=0;int compatible=0;};
        auto eval=[&](int free)->Result {
            u64 mask=free<0?~0ULL:~(1ULL<<free);std::vector<Edge>e;
            for(int u=0;u<P;++u)for(int v=u+1;v<P;++v) {
                u64 d=a[u]^a[v];if(__builtin_popcountll(d)>26)continue;
                int cost=gc(u,v,mask);if(cost<0)continue;
                e.push_back({1800*__builtin_popcountll(d&~low_bits(g))+5*cost+144*__builtin_popcountll(d&mask),u,v});
            }
            Result r;r.compatible=e.size();std::sort(e.begin(),e.end());
            bool used[P]{};int n=0;long long total=0;
            for(auto x:e)if(!used[x.a]&&!used[x.b]) {
                used[x.a]=used[x.b]=true;total+=x.cost;++n;
                if(n==70)r.match70=double(total)/(70*3600);
                if(n==71){r.match71=double(total)/(71*3600);break;}
            }
            if(n<71)r.match71=double(total)/(71*3600)+(71-n)*10.0;
            if(n<70)r.match70=double(total)/(70*3600)+(70-n)*10.0;
            for(auto u:units)if(u.b>=0)r.gc+=gc(u.a,u.b,mask)/720.0/P;
            return r;
        };
        auto base=eval(-1);double meanclose=0,mean70=0,mean71=0,meangc=0;
        int count=0,bestj=-1;Result best;best.match71=1e20;
        for(int j=0;j<g;++j) {
            int copies=0;for(auto e:cmp.edge)copies+=e==cmp.edge[j];
            if(copies<2)continue; // Retain a witness for every generic pair.
            auto r=eval(j);++count;meanclose+=r.compatible;mean70+=r.match70;mean71+=r.match71;meangc+=r.gc;
            if(r.match71<best.match71)best=r,bestj=j;
        }
        std::cout<<argv[f]<<','<<base.compatible<<','<<meanclose/count<<','<<best.compatible<<','
                 <<base.match70<<','<<mean70/count<<','<<mean71/count<<','<<best.match70<<','<<best.match71<<','
                 <<base.gc<<','<<meangc/count<<','<<best.gc<<','<<permutation[bestj]<<'\n';
    }
}
