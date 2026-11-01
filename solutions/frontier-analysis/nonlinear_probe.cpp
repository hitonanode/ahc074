// A design-only probe: retain the 15 comparator edges as a visibility certificate,
// then learn balanced 2-against-2 windows in the 21 redundant positions.
#define main imp_lean_main_for_nonlinear_probe
#include "../imp-lean/main.cpp"
#undef main
#include <iomanip>

using Sat720 = std::array<u64, 12>;
struct NTemplate { unsigned opaque, black; Sat720 one{}; };
struct NPair { int a,b,h,hg; u64 diff; double base; bool ok=false; };

int main() {
    int n,k,p,r;std::cin>>n>>k>>p>>r;
    std::vector<u64>A(p);
    for(auto&a:A){std::string s;std::cin>>s;for(int j=0;j<n;j++)if(s[j]=='1')a|=1ULL<<j;}
    std::mt19937_64 rng(779879);Comparator c;c.init(6,36,rng);
    std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
    assign_windows(A,6,36,c.edge,c.polarity,permutation,1e9,30000,6700,0);c.rebuild();c.build_tables();
    std::vector<NTemplate> templates;
    for(unsigned mask=1;mask<64;mask++) {
        int count=__builtin_popcount(mask);if(count!=2&&count!=4)continue;
        for(unsigned b=mask;b;b=(b-1)&mask)if(__builtin_popcount(b)*2==count){
            NTemplate t{mask,b};
            for(int s=0;s<720;s++)for(int x:c.perms[s])if(mask>>x&1U){if(b>>x&1U)t.one[s/64]|=1ULL<<(s%64);break;}
            templates.push_back(t);
        }
    }
    std::vector<int> window(36);std::vector<bool> locked(36,false);
    unsigned seen=0;
    for(int j=0;j<36;j++) {
        auto[a,b]=c.edge[j];unsigned mask=(1U<<a)|(1U<<b),black=1U<<(c.polarity[j]?a:b);
        for(int t=0;t<int(templates.size());t++)if(templates[t].opaque==mask&&templates[t].black==black)window[j]=t;
        int e=0;for(int x=0;x<a;x++)e+=5-x;e+=b-a-1;
        if(!(seen>>e&1U)){locked[j]=true;seen|=1U<<e;}
    }
    std::vector<u64> shown(720);
    auto rebuild=[&]{for(int s=0;s<720;s++){shown[s]=0;for(int j=0;j<36;j++)shown[s]|=((templates[window[j]].one[s/64]>>(s%64))&1ULL)<<j;}};
    auto sat=[&](int a,u64 d){Sat720 ans{};for(int s=0;s<720;s++)if(!((shown[s]^A[a])&d))ans[s/64]|=1ULL<<(s%64);return ans;};
    auto any=[](const Sat720&s){for(auto x:s)if(x)return true;return false;};
    auto hit=[](const Sat720&a,const Sat720&b,bool one){for(int q=0;q<12;q++)if(a[q]&(one?b[q]:~b[q]))return true;return false;};
    rebuild();
    std::vector<NPair> pairs;
    for(int a=0;a<p;a++)for(int b=a+1;b<p;b++) {
        u64 d=A[a]^A[b];int h=__builtin_popcountll(d);if(h>26)continue;
        int hg=__builtin_popcountll(d&low_bits(36));double base=std::exp((19.95-h+0.30*hg)*0.35);
        pairs.push_back({a,b,h,hg,d&low_bits(36),base});
    }
    auto report=[&](int step){
        struct Edge{double cost,gen;int a,b,hd,h;};std::vector<Edge> edges;
        int compatible=0;
        for(int a=0;a<p;a++)for(int b=a+1;b<p;b++) {
            u64 d=A[a]^A[b];int h=__builtin_popcountll(d);if(h>30)continue;
            auto sa=sat(a,d&low_bits(36)),sb=sat(b,d&low_bits(36));if(!any(sa)||!any(sb))continue;
            compatible+=h<=26;
            std::vector<int> ta,tb;
            for(int s=0;s<720;s++){if(sa[s/64]>>(s%64)&1ULL)ta.push_back(s);if(sb[s/64]>>(s%64)&1ULL)tb.push_back(s);}
            double gen=0;
            for(int s=0;s<720;s++) {
                int x=6,y=6;for(int t:ta)if((x=std::min<int>(x,c.distance(s,t)))==0)break;
                for(int t:tb)if((y=std::min<int>(y,c.distance(s,t)))==0)break;
                gen+=x+y;
            }
            gen/=1440;int hd=__builtin_popcountll(d>>36);
            edges.push_back({0.65*hd+2*gen+0.04*h,gen,a,b,hd,h});
        }
        std::sort(edges.begin(),edges.end(),[](auto&a,auto&b){return a.cost<b.cost;});
        std::vector<bool>used(p,false);int cnt=0,n4=0;double total=0,gen=0,hd=0,h=0;
        for(auto&e:edges){if(used[e.a]||used[e.b])continue;used[e.a]=used[e.b]=true;cnt++;total+=e.cost;gen+=e.gen;hd+=e.hd;h+=e.h;if(cnt==70)break;}
        for(int j=0;j<36;j++)n4+=__builtin_popcount(templates[window[j]].opaque)==4;
        std::cout<<std::fixed<<std::setprecision(6)<<"step "<<step<<" four_windows "<<n4<<" compatible "<<compatible<<" pairs "<<cnt<<" matching "<<total<<" gen "<<gen/cnt<<" handle "<<hd/cnt<<" distance "<<h/cnt<<std::endl;
    };
    report(0);
    for(int step=1;step<=12;step++) {
        std::array<double,256>degree{};
        for(auto& q:pairs){q.ok=any(sat(q.a,q.diff))&&any(sat(q.b,q.diff));if(q.ok){degree[q.a]+=q.base;degree[q.b]+=q.base;}}
        std::array<double,256>values{};for(int a=0;a<256;a++)values[a]=std::pow(degree[a]+0.2,0.7);
        double best=1e-9;int bj=-1,bt=-1;
        for(int j=0;j<36;j++)if(!locked[j]){
            std::vector<Sat720>sa(pairs.size()),sb(pairs.size());std::vector<int>active;
            for(int i=0;i<int(pairs.size());i++) {
                auto&q=pairs[i];if(!(q.diff>>j&1ULL))continue;
                sa[i]=sat(q.a,q.diff&~(1ULL<<j));sb[i]=sat(q.b,q.diff&~(1ULL<<j));
                if(any(sa[i])&&any(sb[i]))active.push_back(i);
            }
            for(int t=0;t<int(templates.size());t++)if(t!=window[j]) {
                std::array<double,256>delta{};
                for(int i:active){auto&q=pairs[i];bool ca=A[q.a]>>j&1ULL,cb=A[q.b]>>j&1ULL;
                    bool ok=hit(sa[i],templates[t].one,ca)&&hit(sb[i],templates[t].one,cb);
                    if(ok==q.ok)continue;double d=ok?q.base:-q.base;delta[q.a]+=d;delta[q.b]+=d;
                }
                double gain=0;for(int a=0;a<256;a++)gain+=std::pow(std::max(0.0,degree[a]+delta[a])+0.2,0.7)-values[a];
                if(gain>best){best=gain;bj=j;bt=t;}
            }
        }
        if(bj<0)break;
        window[bj]=bt;rebuild();
        std::cout<<"accepted "<<step<<" window "<<bj<<" degree_gain "<<best<<std::endl;
        report(step);
    }
}
