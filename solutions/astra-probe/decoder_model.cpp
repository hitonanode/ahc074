// Value of allowing comparator-incompatible pairs, charging a full mean
// decoder cost C for them. C includes helper access, placement, and amortized
// return, less the handle fixes the helper saves. No feasibility is assumed.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"
int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):8,iters=argc>3?std::stoi(argv[3]):2000000;
    std::cout<<"seed,decoder_cost,model,retrieval,handles,decoder,new_pairs\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);std::array<std::array<double,256>,256>base{};
        for(int u=0;u<256;++u)for(int v=u+1;v<256;++v)base[u][v]=base[v][u]=d.cost(u,v,0);
        for(double fee:{-1.0,2.6,3.0,3.4,3.8,4.2}){
            Design des(d.a,6,36);
            auto index=[&](u64 x){return int(std::find(d.a.begin(),d.a.end(),x)-d.a.begin());};
            auto cost=[&](u64 x,u64 y){double b=base[index(x)][index(y)];return b<0?fee:b;};
            bool ok=des.initialize([&](u64 x,u64 y){return cost(x,y)>=0;},cost,[]{return false;});
            if(!ok)return 2;des.anneal(1e9,iters);
            double r=0,h=0,g=0;int novel=0;
            for(int c=0;c<28;++c){r+=des.colcost(c);h+=des.hcost(c);}
            for(auto u:des.unit)if(u.b>=0){g+=des.gc(u);novel+=base[u.a][u.b]<0;}
            std::cout<<seed<<','<<fee<<','<<std::setprecision(10)<<des.cur/256<<','<<r/256<<','<<h/256<<','<<g/256<<','<<novel<<'\n'<<std::flush;
        }
    }
}
