#define main seven_program_main
#include "seven.cpp"
#undef main
#include <iomanip>
int main(){
    int n,k,p,R;std::cin>>n>>k>>p>>R;std::vector<u64>A(p);for(auto&a:A){std::string s;std::cin>>s;for(int j=0;j<63;j++)if(s[j]=='1')a|=1ULL<<j;}
    Comparator c;std::mt19937_64 rng(77);c.init(6,38,rng);
    std::array<std::array<int,6>,6>cnt{};for(auto[x,y]:c.edge)cnt[x][y]++;
    int changed=0;for(int j=0;j<c.G&&changed<4;j++){auto[x,y]=c.edge[j];if(cnt[x][y]>1){cnt[x][y]--;c.edge[j]={x,6};changed++;}}
    c.M=7;c.rebuild();assert(!c.complete);c.build_tables();
    int checked=0;double max_error=0;
    for(int u=0;u<256&&checked<40;u++)for(int v=u+1;v<256&&checked<40;v++)if(c.compatible(A[u],A[v])){
        auto goal=c.satisfying(A[u],A[u]^A[v]);double sum=0;
        for(int s=0;s<5040;s++){int best=255;for(int g:goal)best=std::min(best,c.distance(s,g));sum+=best;}
        double mean=c.mean_moves(A[u],A[u]^A[v]);max_error=std::max(max_error,std::abs(mean-sum/5040));++checked;
    }
    long long moves=0;XorShift rr{971};
    for(int z=0;z<1000;z++){
        int a=rr.mod(5040),b=rr.mod(5040);auto order=c.perms[a];auto path=c.path(a,b);assert(int(path.size())==c.distance(a,b));
        for(auto[sheet,depth]:path){u64 covered=0;bool visible=false;for(int x:order){if(x==sheet){visible=bool(c.opq[x]&~covered);break;}covered|=c.opq[x];}assert(visible);order.erase(std::find(order.begin(),order.end(),sheet));order.insert(order.begin()+depth,sheet);++moves;}
        assert(order==c.perms[b]);
    }
    std::cout<<std::setprecision(15)<<"sparse_exact_pairs = "<<checked<<"\nsparse_max_error = "<<max_error<<"\nsparse_legal_path_moves = "<<moves<<'\n';assert(checked==40&&max_error<1e-12);
}
