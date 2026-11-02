// All costs of a generic paper doubling as the selector, on frozen mappings.
// This model does not read orders. The 720-state legal graph includes the
// selector paper's extra visibility, even when it is the bottom generic paper.
#include <fstream>
#include <iomanip>
#define CAP_COUNT 0
#define CAP_WIDTH 1
#define main research_entry
#include "research.cpp"
#undef main
int main(int argc,char**argv) {
    std::cout<<std::setprecision(12);
    for(int file=1;file<argc;++file) {
        std::ifstream in(argv[file]);int G,C,W,color;in>>G>>C>>W>>color;
        if(!in)return 2;
        std::vector<int>perm(64);for(auto&x:perm)in>>x;
        Comparator comp;comp.M=6;comp.G=G;comp.edge.resize(G);comp.polarity.resize(G);
        for(int j=0;j<G;++j)in>>comp.edge[j].first>>comp.edge[j].second>>comp.polarity[j];
        comp.rebuild();comp.build_tables();
        std::vector<u64>A(P);for(auto&x:A)in>>x;
        const u64 gm=low_bits(G);
        std::vector<u64>display(720);
        std::array<std::vector<u64>,6>through;
        for(auto&v:through)v.resize(720);
        for(int s=0;s<720;++s) {
            u64 cov=0,black=0;
            for(int p:comp.perms[s]) {
                black|=comp.black[p]&~cov;cov|=comp.opq[p];through[p][s]=cov;
            }
            display[s]=black;
        }
        std::array<std::array<unsigned char,P>,P>generic_ok{};
        for(int a=0;a<P;++a)for(int b=a+1;b<P;++b)
            generic_ok[a][b]=generic_ok[b][a]=comp.compatible(A[a],A[b]);
        for(int selector=0;selector<6;++selector)for(int capcolor=0;capcolor<2;++capcolor) {
            if(env_int("ONLY_SELECTOR") && selector+1!=env_int("ONLY_SELECTOR"))continue;
            std::vector<std::vector<int>>adj(720);
            for(int s=0;s<720;++s) {
                u64 covered=0;
                for(int pos=0;pos<6;++pos) {
                    const int paper=comp.perms[s][pos];
                    const bool visible=paper==selector || (comp.opq[paper]&~covered);
                    covered|=comp.opq[paper];
                    if(!visible || pos==5)continue;
                    for(int d=0;d<6;++d) {const int x=comp.next[s][pos*6+d];if(x>=0)adj[s].push_back(x);}
                }
                if(comp.perms[s].back()==selector)for(int d=0;d<5;++d) {
                    auto o=comp.perms[s];o.pop_back();o.insert(o.begin()+d,selector);
                    adj[s].push_back(comp.order_index(o));
                }
            }
            std::vector<unsigned char>dist(720*720,255);
            for(int s=0;s<720;++s) {
                int q[720],lo=0,hi=0;auto*ds=dist.data()+720*s;ds[s]=0;q[hi++]=s;
                while(lo<hi) {
                    int x=q[lo++];for(int y:adj[x])if(ds[y]==255){ds[y]=ds[x]+1;q[hi++]=y;}
                }
            }
            auto ok=std::make_unique<std::array<std::array<unsigned char,P>,P>>();
            auto cost=std::make_unique<std::array<std::array<float,P>,P>>();
            int available=0,close=0,capdiff=0;
            for(int a=0;a<P;++a)for(int b=a+1;b<P;++b)if(generic_ok[a][b]) {
                const u64 holes=(A[a]^A[b])&gm;
                const bool diff=bool((A[a]^A[b])&kCapBit);
                std::vector<int>goals[2];const int us[2]={a,b};
                for(int side=0;side<2;++side) {
                    const int u=us[side];
                    const bool below=diff && bool(A[u]&kCapBit)==bool(capcolor);
                    for(int s=0;s<720;++s)
                        if(!((display[s]^A[u])&(holes|(below?through[selector][s]:0))))goals[side].push_back(s);
                }
                if(goals[0].empty()||goals[1].empty())continue;
                int total=0;
                for(int side=0;side<2;++side)for(int start=0;start<720;++start) {
                    int mn=6;for(int t:goals[side])if((mn=std::min(mn,int(dist[start*720+t])))==0)break;
                    total+=mn;
                }
                (*ok)[a][b]=(*ok)[b][a]=1;(*cost)[a][b]=(*cost)[b][a]=float(total/1440.0);
                ++available;capdiff+=diff;close+=__builtin_popcountll((A[a]^A[b])&kActiveWindows)<=26;
            }
            // Index the targets by barcode: initialization passes full masks.
            auto index=[&](u64 a){return int(std::find(A.begin(),A.end(),a)-A.begin());};
            Design d(A,6,G);
            bool initialized=d.initialize([&](u64 a,u64 b){return bool((*ok)[index(a)][index(b)]);},
                                          [&](u64 a,u64 b){return (*cost)[index(a)][index(b)];},[]{return false;});
            if(!initialized) {
                std::cout<<argv[file]<<','<<selector<<','<<capcolor<<",0,"<<available<<','<<close<<','<<capdiff<<",-1,-1,-1,-1,0\n"<<std::flush;
                continue;
            }
            d.anneal(1e9,20000000);d.filler_climb(1e9,30000);
            double cc=0,hc=0,gc=0;int selected_diff=0;
            for(int c=0;c<d.H;++c)cc+=d.colcost(c),hc+=d.hcost(c);
            for(auto u:d.unit){gc+=d.gc(u);if(u.b>=0)selected_diff+=bool((A[u.a]^A[u.b])&kCapBit);}
            std::cout<<argv[file]<<','<<selector<<','<<capcolor<<",1,"<<available<<','<<close<<','<<capdiff<<','
                     <<(cc+hc+gc)/P<<','<<cc/P<<','<<hc/P<<','<<gc/P<<','<<selected_diff<<'\n'<<std::flush;
        }
    }
}
