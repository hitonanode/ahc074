// Offline structural model, not a contestant or a score evaluation.
// Reuses imp-910's exact legal comparator costs and column annealer read-only.
// An escape bit is implemented by two independent one-bit sheets above the
// generic layer; each consumes two dedicated sheets. All 15 comparator edges
// retain at least one ordinary window so the legal distance table stays valid.
#define main imp910_original_main
#include "../imp-910/main.cpp"
#undef main
#include <bit>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace {
struct Data {
    std::vector<u64> a;
    Comparator comp;
    std::vector<int> physical;
    std::vector<Paper> papers;
    std::vector<int> cols, ded, requests;
    std::vector<std::vector<std::pair<int,int>>> queries;
    std::array<u64,15> edge_windows{};
    explicit Data(int seed) {
        std::ostringstream s;s<<std::setfill('0')<<std::setw(4)<<seed<<".txt";
        std::ifstream in("/home/sato/ahc074/tools/in/"+s.str());
        int n,k,p,r;in>>n>>k>>p>>r;
        std::vector<u64> original(256);
        for(auto&x:original){std::string t;in>>t;for(int j=0;j<64;++j)if(t[j]=='1')x|=1ULL<<j;}
        requests.resize(r);for(int&x:requests)in>>x;
        std::ifstream out("/home/sato/ahc074/runs/20261101-214232_imp-910/out/"+s.str());
        std::vector<Paper> pp(192);
        for(auto&x:pp){std::string t;out>>t;for(int j=0;j<64;++j){if(t[j]!='.')x.opaque|=1ULL<<j;if(t[j]=='1')x.black|=1ULL<<j;}}
        queries.resize(r);for(auto&q:queries){int m;out>>m;q.resize(m);for(auto&[x,y]:q)out>>x>>y;}
        u64 gm=0;for(int k=0;k<6;++k)gm|=pp[k].opaque;
        for(int j=0;j<64;++j)if(gm>>j&1)physical.push_back(j);
        std::vector<int> hs;
        for(int j=0;j<64;++j)if(!(gm>>j&1))hs.push_back(j);
        auto first=[&](int j){for(int k=6;k<192;++k)if(pp[k].opaque>>j&1)return k;return 192;};
        std::sort(hs.begin(),hs.end(),[&](int x,int y){return first(x)<first(y);});
        physical.insert(physical.end(),hs.begin(),hs.end());
        assert(std::popcount(gm)==36);
        a.assign(256,0);for(int u=0;u<256;++u)for(int j=0;j<64;++j)a[u]|=((original[u]>>physical[j])&1)<<j;
        papers.resize(192);cols.assign(192,-1);ded.assign(256,-1);
        for(int k=0;k<192;++k)for(int j=0;j<64;++j){papers[k].opaque|=((pp[k].opaque>>physical[j])&1)<<j;papers[k].black|=((pp[k].black>>physical[j])&1)<<j;}
        for(int k=6;k<192;++k){
            for(int c=0;c<28;++c)if(first(hs[c])<=k)cols[k]=c;
            for(int u=0;u<256;++u)if((a[u]&papers[k].opaque)==papers[k].black){assert(ded[u]<0);ded[u]=k;}
        }
        assert(std::find(ded.begin(),ded.end(),-1)==ded.end());
        comp.M=6;comp.G=36;
        for(int j=0;j<36;++j){
            std::vector<int> v;for(int k=0;k<6;++k)if(pp[k].opaque>>physical[j]&1)v.push_back(k);
            assert(v.size()==2);
            comp.edge.emplace_back(v[0],v[1]);comp.polarity.push_back(pp[v[0]].black>>physical[j]&1);
            int eid=0;for(int x=0;x<v[0];++x)eid+=5-x;eid+=v[1]-v[0]-1;
            edge_windows[eid]|=1ULL<<j;
        }
        comp.rebuild();assert(comp.complete);
    }
    bool valid_escape(u64 mask) const {
        for(u64 e:edge_windows)if(!(e&~mask))return false;
        return true;
    }
    // Returns exact generic-layer mean plus 1/2 per active independent escape
    // bit. For a two-sheet multi-bit switch, all active bits must match +/- Y.
    double cost(int u,int v,u64 mask,bool grouped=false,u64 pattern=0) const {
        const u64 delta=a[u]^a[v],esc=delta&mask;
        if(grouped && (a[u]^pattern)&esc && ((a[u]^pattern)&esc)!=esc)return -1;
        const auto cl=comp.closure(a[u],delta&~mask);
        u64 rel=0;for(int x=0;x<6;++x){if(cl[x]>>x&1)return -1;rel|=u64(cl[x])<<(8*x);}
        return PosetSums::get().both_of(rel)/1440.0+0.5*(grouped?bool(esc):std::popcount(esc));
    }
    double greedy(u64 mask,bool grouped=false,u64 pattern=0) const {
        struct Edge {double c;int u,v;};std::vector<Edge> e;
        for(int u=0;u<256;++u)for(int v=u+1;v<256;++v){
            double c=cost(u,v,mask,grouped,pattern);if(c<0)continue;
            u64 delta=a[u]^a[v];e.push_back({.65*std::popcount(delta>>36)+2*c+.04*std::popcount(delta),u,v});
        }
        std::sort(e.begin(),e.end(),[](const Edge&a,const Edge&b){if(a.c!=b.c)return a.c<b.c;return std::pair(a.u,a.v)<std::pair(b.u,b.v);});
        std::array<bool,256> used{};int n=0;double val=0;
        const int need=70+2*(grouped?bool(mask):std::popcount(mask));
        for(auto x:e)if(!used[x.u]&&!used[x.v]){used[x.u]=used[x.v]=true;val+=x.c;if(++n==need)break;}
        return n==need?val/256:1e9;
    }
    void model(int seed,u64 mask,int iters,bool grouped=false,u64 pattern=0) const {
        Design d(a,6,36);
        d.U=186-2*(grouped?bool(mask):std::popcount(mask));d.need=256-d.U;
        auto compatible=[&](u64 x,u64 y){
            const u64 esc=(x^y)&mask;
            if(grouped && (x^pattern)&esc && ((x^pattern)&esc)!=esc)return false;
            return comp.compatible(x&~mask,y&~mask);
        };
        auto estimate=[&](u64 x,u64 y){
            const auto cl=comp.closure(x,(x^y)&~mask);u64 rel=0;
            for(int k=0;k<6;++k)rel|=u64(cl[k])<<(8*k);
            return PosetSums::get().both_of(rel)/1440.0+.5*(grouped?bool((x^y)&mask):std::popcount((x^y)&mask));
        };
        if(!d.initialize(compatible,estimate,[]{return false;})){std::cerr<<"init failed "<<seed<<' '<<mask<<'\n';return;}
        d.anneal(1e9,iters);
        double retrieve=0,holes=0,generic=0,escape=0;
        for(int c=0;c<28;++c){retrieve+=d.colcost(c);holes+=d.hcost(c);}
        for(auto u:d.unit)if(u.b>=0){
            double es=(grouped?bool((a[u.a]^a[u.b])&mask):std::popcount((a[u.a]^a[u.b])&mask));
            escape+=es;generic+=d.gc(u)-es;
        }
        int compatible_count=0;for(int u=0;u<256;++u)for(int v=u+1;v<256;++v)compatible_count+=d.ok[u][v];
        std::cout<<seed<<','<<(grouped?"switch":"bits")<<','<<std::popcount(mask)<<','<<mask<<','<<pattern<<','<<d.U<<','<<compatible_count<<','<<std::setprecision(10)<<d.cur/256<<','<<retrieve/256<<','<<holes/256<<','<<generic/256<<','<<escape/256<<','<<greedy(mask,grouped,pattern)<<'\n'<<std::flush;
    }
};

std::unique_ptr<Solver> make_solver(Data&d,bool helpers=true) {
    d.comp.build_tables();auto ptr=std::make_unique<Solver>(d.a);auto&s=*ptr;
    s.M=6;s.G=36;s.H=28;s.comparator=d.comp;s.paper=d.papers;s.col_of=d.cols;s.ded=d.ded;
    s.gmask=low_bits(36);s.hmask=~s.gmask;s.handle.resize(28);s.hidx.assign(64,-1);
    for(int c=0;c<28;++c){s.handle[c]=36+c;s.hidx[36+c]=c;}
    s.h_opq.resize(192);s.h_blk.resize(192);
    for(int k=0;k<192;++k){s.h_opq[k]=s.paper[k].opaque>>36;s.h_blk[k]=s.paper[k].black>>36;}
    s.order.resize(192);std::iota(s.order.begin(),s.order.end(),0);s.init_adaptive();
    if(helpers){s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);}
    return ptr;
}
}

#ifndef ASTRA_NO_ESCAPE_MAIN
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8,iters=argc>3?std::stoi(argv[3]):2000000;
    std::cout<<"seed,kind,q,mask,pattern,dedicated,compatible,model,retrieval,handle_holes,generic,escape,greedy\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);u64 mask=0;d.model(seed,mask,iters);
        for(int q=1;q<=4;++q){
            double best=1e99;u64 next=0;
            for(int j=0;j<36;++j)if(!(mask>>j&1)&&d.valid_escape(mask|(1ULL<<j))){
                u64 m=mask|(1ULL<<j);double c=d.greedy(m);
                if(c<best){best=c;next=m;}
            }
            mask=next;d.model(seed,mask,iters);
        }
        // Choose one two-bit complementary switch (2 extra papers), all pairs
        // of windows and both relative polarities; keep comparator complete.
        double best=1e99;u64 sm=0,sy=0;
        for(int x=0;x<36;++x)for(int y=x+1;y<36;++y){
            u64 m=(1ULL<<x)|(1ULL<<y);if(!d.valid_escape(m))continue;
            for(int pol=0;pol<2;++pol){u64 yy=pol?1ULL<<y:0;double c=d.greedy(m,true,yy);if(c<best){best=c;sm=m;sy=yy;}}
        }
        d.model(seed,sm,iters,true,sy);
    }
}
#endif
