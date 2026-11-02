#define main seven_program_main
#include "seven.cpp"
#undef main
#include <iomanip>
int main(){
    int n,k,p,R;std::cin>>n>>k>>p>>R;std::vector<u64>A(p);for(auto&a:A){std::string s;std::cin>>s;for(int j=0;j<63;j++)if(s[j]=='1')a|=1ULL<<j;}
    Comparator c;std::mt19937_64 rng(77);c.init(7,38,rng);c.build_tables();
    int checked=0;double max_error=0;
    for(int u=0;u<256&&checked<100;u++)for(int v=u+1;v<256&&checked<100;v++)if(c.compatible(A[u],A[v])){
        auto reach=c.closure(A[u],A[u]^A[v]);u64 rel=0;for(int x=0;x<7;x++)rel|=u64(reach[x])<<(8*x);
        double expected=(Poset7Costs::get().cost(rel)-1)/10080.0;
        double actual=.5*(c.mean_moves(A[u],A[u]^A[v])+c.mean_moves(A[v],A[u]^A[v]));
        max_error=std::max(max_error,std::abs(actual-expected));++checked;
    }
    long long moves=0;XorShift rr{971};
    for(int z=0;z<1000;z++){
        int a=rr.mod(5040),b=rr.mod(5040);auto order=c.perms[a];auto path=c.path(a,b);
        assert(int(path.size())==c.distance(a,b));
        for(auto[sheet,depth]:path){u64 covered=0;bool visible=false;for(int x:order){if(x==sheet){visible=bool(c.opq[x]&~covered);break;}covered|=c.opq[x];}assert(visible);order.erase(std::find(order.begin(),order.end(),sheet));order.insert(order.begin()+depth,sheet);++moves;}
        assert(order==c.perms[b]);
    }
    std::cout<<std::setprecision(15)<<"seven_exact_pairs = "<<checked<<"\nseven_max_error = "<<max_error<<"\nseven_legal_path_moves = "<<moves<<'\n';
    assert(checked==100&&max_error<1e-12);
}
