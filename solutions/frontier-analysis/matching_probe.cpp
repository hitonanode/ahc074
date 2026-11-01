#define main imp_lean_main_for_probe
#include "../imp-lean/main.cpp"
#undef main
#include <iomanip>

int main() {
    int n,k,p,r;
    std::cin >> n >> k >> p >> r;
    std::vector<u64> A(p);
    for (auto &a : A) {
        std::string s; std::cin >> s;
        for (int j=0;j<n;j++) if(s[j]=='1') a |= 1ULL<<j;
    }
    std::mt19937_64 rng(779879);
    Comparator base; base.init(6,36,rng);
    std::vector<int> permutation(64); std::iota(permutation.begin(),permutation.end(),0);
    assign_windows(A,6,36,base.edge,base.polarity,permutation,1e9,30000,6700,0);
    base.rebuild();
    for(int m=6;m<=9;m++) {
        Comparator c;
        if(m==6)c=base; else c.init(m,36,rng);
        std::vector<std::vector<int>> orders;
        for(int s=0;s<24;s++) {
            std::vector<int> v(m); std::iota(v.begin(),v.end(),0);
            std::shuffle(v.begin(),v.end(),rng); orders.push_back(v);
        }
        struct Edge{double value,gen;int a,b,dh,d;};
        std::vector<Edge> e;
        int nearby=0,oknear=0;
        for(int a=0;a<p;a++) for(int b=a+1;b<p;b++) {
            const auto diff=A[a]^A[b];
            int d=__builtin_popcountll(diff), dh=__builtin_popcountll(diff>>36);
            if(d<=26)nearby++;
            if(!c.compatible(A[a],A[b]))continue;
            if(d<=26)oknear++;
            if(d>30)continue;
            double gen=0;
            for(auto &ord:orders) {
                gen+=c.plan(ord,A[a],diff).size();
                gen+=c.plan(ord,A[b],diff).size();
            }
            gen/=2*orders.size();
            e.push_back({0.65*dh+2*gen+0.04*d,gen,a,b,dh,d});
        }
        std::sort(e.begin(),e.end(),[](auto&a,auto&b){return a.value<b.value;});
        std::vector<bool> used(p,false);
        double cost=0,gen=0,dh=0,d=0;int pairs=0;
        for(auto &x:e) {
            if(used[x.a]||used[x.b])continue;
            used[x.a]=used[x.b]=true;
            cost+=x.value;gen+=x.gen;dh+=x.dh;d+=x.d;
            if(++pairs==64+m)break;
        }
        std::cout<<std::fixed<<std::setprecision(6)<<"M "<<m<<" nearby "<<nearby<<" compatible "<<oknear
            <<" pairs "<<pairs<<" objective "<<cost<<" mean_gen "<<gen/pairs<<" mean_handle_diff "<<dh/pairs
            <<" mean_diff "<<d/pairs<<" gen_per_request "<<2*gen/256<<std::endl;
    }
}
