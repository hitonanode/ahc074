// Enumeration of feasible three-target papers under the saved comparator.
#define ASTRA_NO_ESCAPE_MAIN
#include "escape_model.cpp"

int main(int argc,char**argv){
    int lo=argc>1?std::stoi(argv[1]):0,hi=argc>2?std::stoi(argv[2]):16;
    std::cout<<"seed,compatible_pairs,pair_cliques,feasible_triples,best_triple_proxy_per_saved_paper,min_variable_G,min_variable_H,mean_generic_per_target\n";
    for(int seed=lo;seed<hi;++seed){
        Data d(seed);std::array<std::array<bool,256>,256> ok{};
        int pairs=0,cliques=0,feasible=0,min_g=64,min_h=64;
        double best=1e99,total_g=0;
        for(int a=0;a<256;++a)for(int b=a+1;b<256;++b)pairs+=(ok[a][b]=ok[b][a]=d.cost(a,b,0)>=0);
        for(int a=0;a<256;++a)for(int b=a+1;b<256;++b)if(ok[a][b])for(int c=b+1;c<256;++c)if(ok[a][c]&&ok[b][c]){
            ++cliques;u64 delta=(d.a[a]^d.a[b])|(d.a[a]^d.a[c]);double gc=0;bool valid=true;
            for(int u:{a,b,c}){
                auto cl=d.comp.closure(d.a[u],delta);u64 r=0;
                for(int k=0;k<6;++k){valid&=!(cl[k]>>k&1);r|=u64(cl[k])<<(8*k);}
                if(!valid)break;
                const auto&t=PosetSums::get();gc+=t.one[t.slot_of(r)]/720.0;
            }
            if(!valid)continue;++feasible;total_g+=gc/3;
            min_g=std::min(min_g,std::popcount(delta&low_bits(36)));
            min_h=std::min(min_h,std::popcount(delta>>36));
            // Optimistic proxy: 2/3 of variable handle bits are already opaque
            // prefix bits at the typical column; triangle holes cancel.
            best=std::min(best,(gc+.4*3*(2.0/3)*std::popcount(delta>>36))/2);
        }
        std::cout<<seed<<','<<pairs<<','<<cliques<<','<<feasible<<','<<best<<','<<min_g<<','<<min_h<<','<<(feasible?total_g/feasible:0)<<'\n'<<std::flush;
    }
}
