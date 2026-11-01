// Assert incremental mapping costs against complete recomputation after every accepted move.
#define CLIQUE_CHECK
#define main frontier_clique_submission_main
#include "../frontier-clique/main.cpp"
#undef main

int main() {
    int n,k,p,r;
    std::cin>>n>>k>>p>>r;
    std::vector<u64> original(p);
    for(auto& a:original) {
        std::string s;std::cin>>s;
        for(int j=0;j<n;j++) if(s[j]=='1')a|=1ULL<<j;
    }
    for(int m:{9,10}) {
        auto A=original;
        std::mt19937_64 rng(779879);
        Comparator c;c.init(m,m*(m-1)/2,rng);
        std::vector<int> perm(64);std::iota(perm.begin(),perm.end(),0);
        auto stats=assign_windows_clique(A,m,m*(m-1)/2,c.edge,c.polarity,perm,1e9,300,0,0);
        std::cout<<"checked_m = "<<m<<" iterations = "<<stats.iterations<<'\n';
    }
}
