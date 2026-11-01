// Optional asymmetric one-bit patches: an infeasible pair may print one
// differing bit, using a sparse patch above D for only one endpoint. This is
// an optimistic model: the patch's storage handle is not charged or checked.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"

double patch_cost(const Data& d,int u,int v,u64 mask,double fee) {
    double normal=d.cost(u,v,0), patched=d.cost(u,v,mask);
    if(patched>=0)patched+=fee-.5*std::popcount((d.a[u]^d.a[v])&mask);
    if(!((d.a[u]^d.a[v])&mask))patched=-1;
    if(normal<0)return patched;
    if(patched<0)return normal;
    return std::min(normal,patched);
}
double patch_greedy(const Data&d,u64 mask,double fee) {
    struct E{double cost;int u,v;};std::vector<E> es;
    for(int u=0;u<256;++u)for(int v=u+1;v<256;++v){
        double c=patch_cost(d,u,v,mask,fee);if(c<0)continue;
        u64 delta=d.a[u]^d.a[v];es.push_back({.65*std::popcount(delta>>36)+2*c+.04*std::popcount(delta),u,v});
    }
    std::sort(es.begin(),es.end(),[](E a,E b){return a.cost<b.cost;});
    int count=0;double cost=0;std::array<bool,256>used{};
    for(auto e:es)if(!used[e.u]&&!used[e.v]){
        used[e.u]=used[e.v]=true;cost+=e.cost;if(++count==70+std::popcount(mask))break;
    }
    return count==70+std::popcount(mask)?cost:1e9;
}
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8,iters=argc>3?std::stoi(argv[3]):2000000;
    std::cout<<"seed,fee,mask,model,retrieval,handles,decoder,used_patched_pairs,new_incompatible_pairs\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);
        for(double fee:{0.0,0.6,0.9,1.2}){
            u64 mask=0;
            if(fee>0){double best=1e99;for(int j=0;j<36;++j){double c=patch_greedy(d,1ULL<<j,fee);if(c<best){best=c;mask=1ULL<<j;}}}
            Design des(d.a,6,36);des.U=186-std::popcount(mask);des.need=256-des.U;
            std::array<std::array<double,256>,256>cost{};
            for(int u=0;u<256;++u)for(int v=u+1;v<256;++v)cost[u][v]=cost[v][u]=patch_cost(d,u,v,mask,fee);
            auto index=[&](u64 x){return int(std::find(d.a.begin(),d.a.end(),x)-d.a.begin());};
            bool ok=des.initialize([&](u64 x,u64 y){return cost[index(x)][index(y)]>=0;},[&](u64 x,u64 y){return cost[index(x)][index(y)];},[]{return false;});
            if(!ok){std::cerr<<"failed\n";return 2;}
            des.anneal(1e9,iters);
            double r=0,h=0,g=0;int uses=0,newpairs=0;
            for(int c=0;c<28;++c){r+=des.colcost(c);h+=des.hcost(c);}
            for(auto u:des.unit)if(u.b>=0){
                g+=des.gc(u);double normal=d.cost(u.a,u.b,0);
                if(normal<0||cost[u.a][u.b]<normal-1e-6){++uses;newpairs+=normal<0;}
            }
            std::cout<<seed<<','<<fee<<','<<mask<<','<<std::setprecision(10)<<des.cur/256<<','<<r/256<<','<<h/256<<','<<g/256<<','<<uses<<','<<newpairs<<'\n'<<std::flush;
        }
    }
}
