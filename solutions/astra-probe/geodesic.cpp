// Verify the input-dependent universal lower bound; this does not run a solver.
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
using U = std::uint64_t;
int main(int argc,char**argv) {
    const int lo=argc>1?std::stoi(argv[1]):0, hi=argc>2?std::stoi(argv[2]):2000;
    const std::string root="/home/sato/ahc074/tools/in/";
    std::cout << "seed,min_distance,geodesic_triples,mean_one_step_upper,expected_moves_lower,mean_nearest_distance,distance_one_step_upper,distance_expected_lower\n";
    for(int seed=lo;seed<hi;++seed){
        std::ostringstream name; name<<root<<std::setfill('0')<<std::setw(4)<<seed<<".txt";
        std::ifstream f(name.str()); int n,k,p,r;f>>n>>k>>p>>r;
        if(!f || n!=64 || p!=256) return 2;
        std::array<U,256> a{};
        for(U& x:a){std::string s;f>>s;for(int j=0;j<64;++j)if(s[j]=='1')x|=U(1)<<j;}
        int mn=64, triples=0;std::array<int,256> incidence{},nearest{};nearest.fill(64);
        for(int u=0;u<256;++u)for(int v=u+1;v<256;++v){
            const U uv=a[u]^a[v];int delta=std::popcount(uv);mn=std::min(mn,delta);
            nearest[u]=std::min(nearest[u],delta);nearest[v]=std::min(nearest[v],delta);
            for(int w=v+1;w<256;++w){
                const U uw=a[u]^a[w];
                if(!(uv&uw) || !(uv&~uw) || !(uw&~uv)){
                    ++triples;++incidence[u];++incidence[v];++incidence[w];
                }
            }
        }
        double one=0;
        for(int x:incidence)one+=std::min(255,64+x)/256.0;
        // Subsequent queries: 2-one/255. Initial query: >=1-1/256.
        const double bound=((r-1)*(2-one/255)+(1-1/256.0))/r;
        double tight=0,mean_distance=0;
        for(int u=0;u<256;++u){tight+=std::min(255,64-nearest[u]+1+incidence[u])/256.0;mean_distance+=nearest[u]/256.0;}
        const double strong=((r-1)*(2-tight/255)+(1-1/256.0))/r;
        std::cout<<seed<<','<<mn<<','<<triples<<','<<one<<','<<std::setprecision(12)<<bound<<','<<mean_distance<<','<<tight<<','<<strong<<'\n';
    }
}
