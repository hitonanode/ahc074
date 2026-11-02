// Design-only diagnostic. No requests are read and no contest score is emitted.
#define main ahc_original_main
#ifdef BASELINE_PROBE
#include "../astra-search4/main.cpp"
#else
#include "main.cpp"
#endif
#undef main
int main() {
    int n,k,p,r;
    if(!(std::cin>>n>>k>>p>>r))return 1;
    std::vector<u64> a(p);
    for(auto& x:a){std::string s;std::cin>>s;x=0;for(int j=0;j<n;++j)if(s[j]=='1')x|=1ULL<<j;}
    std::mt19937_64 rng(779879);
    Comparator comp;comp.init(6,36,rng);
    std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
    const auto t=std::chrono::steady_clock::now();
    const auto ws=assign_windows(a,6,36,comp.edge,comp.polarity,permutation,1e9,env_int("MAP_ITERS"),env_int("GOPT_STEPS"),0.0);
    std::cerr<<"probe_gobj = "<<ws.gobj_after<<"\nprobe_iters = "<<ws.iterations+ws.climb_steps
             <<"\nprobe_map_sec = "<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count()<<'\n';
    return 0;
}
