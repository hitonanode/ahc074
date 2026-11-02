// Exact six-sheet cycle relaxations and a fully charged two-cap design model.
// Research only: includes the current-lineage model, never an executable solution.
#define main model_program_main
#include "model.cpp"
#undef main
#include <fstream>
#include <iomanip>
#include <unordered_map>

int main(int argc,char**argv) {
    if(argc<2)return 2;
    std::ifstream in(argv[1]); int seed,G;in>>seed>>G;
    std::vector<u64>A(256);for(auto&x:A)in>>x;
    std::array<int,256>cap{};for(auto&x:cap)in>>x;
    Comparator c;c.M=6;c.G=G;c.edge.resize(G);c.polarity.resize(G);
    for(int j=0;j<G;j++)in>>c.edge[j].first>>c.edge[j].second>>c.polarity[j];
    c.rebuild();
    std::unordered_map<u64,int>id;for(int i=0;i<256;i++)id[A[i]]=i;
    std::vector<u64>displays;std::vector<int>order{0,1,2,3,4,5};
    do{u64 covered=0,b=0;for(int k:order){b|=c.black[k]&~covered;covered|=c.opq[k];}displays.push_back(b);}while(std::next_permutation(order.begin(),order.end()));
    using Mat=std::array<std::array<double,256>,256>;
    auto base=std::make_unique<Mat>();for(auto&r:*base)r.fill(-1);
    std::array<std::array<int,256>,256>fas{};
    auto gc=[&](int u,int v,u64 remove=0) {
        auto reach=c.closure(A[u],(A[u]^A[v])&~remove);u64 r=0;
        for(int k=0;k<6;k++)r|=u64(reach[k])<<(8*k);
        if(r&kDiagonal)return -1.0;
        return PosetSums::get().both_of(r)/1440.0;
    };
    for(int u=0;u<256;u++)for(int v=u+1;v<256;v++) {
        (*base)[u][v]=(*base)[v][u]=gc(u,v);
        int best=99;u64 d=(A[u]^A[v])&low_bits(G);
        if(__builtin_popcountll(A[u]^A[v])<=26)for(u64 display:displays)best=std::min(best,__builtin_popcountll((display^A[u])&d));
        fas[u][v]=fas[v][u]=best;
    }
    auto make=[&](const Mat&cost,int m) {
        auto d=std::make_unique<Design>(A,m,G);
        bool ok=d->initialize([&](u64 a,u64 b){return cost[id[a]][id[b]]>=0;},[&](u64 a,u64 b){return cost[id[a]][id[b]];},[]{return false;});
        if(!ok)d.reset();return d;
    };
    auto emit=[&](const std::string&name,std::unique_ptr<Design>d,int window=-1,int capcolor=-1,int caporder=-1) {
        if(!d){std::cout<<"{\"seed\":"<<seed<<",\"mode\":\""<<name<<"\",\"failed\":true}\n"<<std::flush;return 1e9;}
        d->anneal(1e9,20000000);d->filler_climb(1e9,60000);
        double col=0,hole=0,generic=0,gh=0,sh=0;int incompat=0,pairs=0;
        for(int j=0;j<d->H;j++){col+=d->colcost(j);hole+=d->hcost(j);}
        for(const auto&u:d->unit)if(u.b>=0){++pairs;generic+=d->gc(u);incompat+=(*base)[u.a][u.b]<0;gh+=__builtin_popcountll((A[u.a]^A[u.b])&low_bits(G));sh+=__builtin_popcountll((d->hb[u.a]^d->hb[u.b])&low_bits(u.c+1));}
        double val=(col+hole+generic)/256;
        std::cout<<std::setprecision(12)<<"{\"seed\":"<<seed<<",\"mode\":\""<<name<<"\",\"model_cost\":"<<val<<",\"model_col\":"<<col/256<<",\"model_hole\":"<<hole/256<<",\"model_gc\":"<<generic/256<<",\"pair_gc_mean\":"<<generic/(2*pairs)<<",\"pair_generic_hd\":"<<gh/pairs<<",\"pair_shallow_hd\":"<<sh/pairs<<",\"pairs_incompat\":"<<incompat<<",\"pairs\":"<<pairs<<",\"window\":"<<window<<",\"capcolor\":"<<capcolor<<",\"caporder\":"<<caporder<<"}\n"<<std::flush;
        return val;
    };
    for(int f=1;f<=4;f++){
        auto cost=std::make_unique<Mat>(*base);
        for(int u=0;u<256;u++)for(int v=u+1;v<256;v++)if((*cost)[u][v]<0&&fas[u][v]<=f)(*cost)[u][v]=(*cost)[v][u]=2.46;
        emit("fas"+std::to_string(f),make(*cost,6));
    }
    // All choices obey the actual three insertion depths of D around two fixed
    // caps, including equal bits at one cap. D's two printed bits are chosen
    // per pair. This avoids counting four independent binary choices for two caps.
    auto cap_pair_ok=[&](int u,int v,int w,int color,int reverse){
        const int target[2]={cap[u]*2+int(A[u]>>w&1),cap[v]*2+int(A[v]>>w&1)};
        for(int print=0;print<4;print++){
            unsigned possible=1U<<print;
            int middle=reverse?((print&2)|color):(2|(print&1));
            possible|=1U<<middle;possible|=1U<<(2|color);
            if((possible>>target[0]&1)&&(possible>>target[1]&1))return true;
        }return false;
    };
    struct CapOption{double init;int w,color,rev;};std::vector<CapOption>options;
    double bestfree=1e100;int freew=-1;
    for(int w=0;w<G;w++) {
        auto costs=std::make_unique<Mat>();for(auto&r:*costs)r.fill(-1);
        for(int u=0;u<256;u++)for(int v=u+1;v<256;v++)(*costs)[u][v]=(*costs)[v][u]=gc(u,v,1ULL<<w);
        auto fd=make(*costs,6);if(fd&&fd->cur<bestfree)bestfree=fd->cur,freew=w;
        // A removed witness is not assumed to leave all five non-bottom sheets
        // visible. Restrict executable fixed-cap candidates to redundant edges.
        int count=0;for(auto e:c.edge)count+=e==c.edge[w];if(count<2)continue;
        for(int color=0;color<2;color++)for(int rev=0;rev<2;rev++){
            auto cc=std::make_unique<Mat>(*costs);
            for(int u=0;u<256;u++)for(int v=u+1;v<256;v++)if(!cap_pair_ok(u,v,w,color,rev))(*cc)[u][v]=(*cc)[v][u]=-1;
            auto d=make(*cc,7);if(d)options.push_back({d->cur,w,color,rev});
        }
    }
    if(freew>=0){auto costs=std::make_unique<Mat>();for(auto&r:*costs)r.fill(-1);for(int u=0;u<256;u++)for(int v=u+1;v<256;v++)(*costs)[u][v]=(*costs)[v][u]=gc(u,v,1ULL<<freew);emit("shared1_free",make(*costs,6),freew);}
    std::sort(options.begin(),options.end(),[](auto&a,auto&b){return a.init<b.init;});
    for(int k=0;k<std::min<int>(4,options.size());k++){
        auto o=options[k];auto costs=std::make_unique<Mat>();for(auto&r:*costs)r.fill(-1);
        for(int u=0;u<256;u++)for(int v=u+1;v<256;v++)if(cap_pair_ok(u,v,o.w,o.color,o.rev))(*costs)[u][v]=(*costs)[v][u]=gc(u,v,1ULL<<o.w);
        emit("cap2_"+std::to_string(k),make(*costs,7),o.w,o.color,o.rev);
    }
}
