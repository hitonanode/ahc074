#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <string>
#include <vector>
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using U=std::uint64_t;
using Rows=std::array<unsigned,20>;
struct Triple {int a,b,c,holes,handle_holes;double fee=0;};
struct Problem {
    int M,G;std::array<U,256>A{};std::vector<std::pair<int,int>> edge;
    std::array<std::array<Rows,256>,256> pair_reach{};
    std::array<std::array<bool,256>,256> compatible{};
    std::vector<std::array<unsigned,20>> prefixes;
    U gm;
    Problem(const char* path,int m,int g,int mapping):M(m),G(g),gm((U(1)<<g)-1){
        std::ifstream in(path);int n,k,p,r;in>>n>>k>>p>>r;std::string s;
        for(auto& a:A){in>>s;for(int j=0;j<63;j++)if(s[j]=='1')a|=U(1)<<j;}
        std::mt19937_64 rng(729871+mapping);std::vector<int> windows(63);std::iota(windows.begin(),windows.end(),0);std::shuffle(windows.begin(),windows.end(),rng);
        for(auto& a:A){U b=0;for(int j=0;j<63;j++)b|=((a>>windows[j])&1)<<j;a=b;}
        std::vector<std::pair<int,int>> all;for(int a=0;a<M;a++)for(int b=a+1;b<M;b++)all.emplace_back(a,b);std::shuffle(all.begin(),all.end(),rng);
        for(int j=0;j<G;j++){auto e=all[j%all.size()];if(rng()&1)std::swap(e.first,e.second);edge.push_back(e);}
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){
            Rows reach{};bool ok=extend(reach,A[a],(A[a]^A[b])&gm);compatible[a][b]=compatible[b][a]=ok;
            if(ok){pair_reach[a][b]=reach;for(int x=0;x<M;x++)for(int y=0;y<M;y++)if(reach[x]>>y&1)pair_reach[b][a][y]|=1U<<x;}
        }
        std::array<int,20> order{};std::iota(order.begin(),order.begin()+M,0);
        for(int i=0;i<32;i++){std::shuffle(order.begin(),order.begin()+M,rng);std::array<unsigned,20> before{};unsigned seen=0;for(int j=0;j<M;j++){before[order[j]]=seen;seen|=1U<<order[j];}prefixes.push_back(before);}
    }
    bool extend(Rows& reach,U target,U holes)const{
        for(U z=holes;z;z&=z-1){int j=std::countr_zero(z);auto[a,b]=edge[j];if(!(target>>j&1))std::swap(a,b);
            if(reach[b]>>a&1)return false;if(reach[a]>>b&1)continue;
            unsigned following=reach[b]|(1U<<b);for(int x=0;x<M;x++)if(x==a||(reach[x]>>a&1))reach[x]|=following;
        }
        return true;
    }
    double lower_cost(const Rows& reach,int samples=8)const{
        // Inverted precedence pairs form a partial order. An unchanged
        // subsequence is an antichain of this order. By Dilworth's theorem,
        // the minimum number of arbitrary moves is its maximum matching size.
        double total=0;
        for(int sample=0;sample<samples;sample++){
            std::array<unsigned,20> inversion{};for(int x=0;x<M;x++)inversion[x]=reach[x]&prefixes[sample][x];
            std::array<int,20> matched;matched.fill(-1);int cardinality=0;
            auto augment=[&](auto&& self,int x,unsigned& visited)->bool{
                for(unsigned z=inversion[x]&~visited;z;z&=z-1){int y=std::countr_zero(z);visited|=1U<<y;if(matched[y]<0||self(self,matched[y],visited)){matched[y]=x;return true;}}
                return false;
            };
            for(int x=0;x<M;x++){unsigned visited=0;if(augment(augment,x,visited))cardinality++;}
            total+=cardinality;
        }
        return total/samples;
    }
};
int main(int argc,char** argv){
    if(argc<4)return 2;int m=std::stoi(argv[2]),g=std::stoi(argv[3]),map=argc>4?std::stoi(argv[4]):0;
    auto start=std::chrono::steady_clock::now();auto p=std::make_unique<Problem>(argv[1],m,g,map);
    int pairs=0,near_pairs=0,triangles=0,triples=0,near_triples=0;double mean_union=0;std::vector<Triple> candidates;
    for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p->compatible[a][b]){pairs++;near_pairs+=std::popcount(p->A[a]^p->A[b])<=26;}
    for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(p->compatible[a][b])for(int c=b+1;c<256;c++)if(p->compatible[a][c]&&p->compatible[b][c]){
        triangles++;U holes=(p->A[a]^p->A[b])|(p->A[a]^p->A[c]);if(std::popcount(holes)>42)continue;
        auto ra=p->pair_reach[a][b],rb=p->pair_reach[b][a],rc=p->pair_reach[c][a];
        if(!p->extend(ra,p->A[a],holes&p->gm&~(p->A[a]^p->A[b])))continue;
        if(!p->extend(rb,p->A[b],holes&p->gm&~(p->A[a]^p->A[b])))continue;
        if(!p->extend(rc,p->A[c],holes&p->gm&~(p->A[a]^p->A[c])))continue;
        triples++;mean_union+=std::popcount(holes);if(std::popcount(holes)>38)continue;near_triples++;
        double fee=p->lower_cost(ra)+p->lower_cost(rb)+p->lower_cost(rc);
        candidates.push_back({a,b,c,std::popcount(holes),std::popcount(holes&~p->gm),fee});
    }
    std::sort(candidates.begin(),candidates.end(),[](const auto& a,const auto& b){return a.fee+.975*a.handle_holes+.06*a.holes<b.fee+.975*b.handle_holes+.06*b.holes;});
    std::array<bool,256> used{};int chosen=0;double cost=0,hole=0,hh=0;
    for(auto t:candidates)if(!used[t.a]&&!used[t.b]&&!used[t.c]){used[t.a]=used[t.b]=used[t.c]=true;chosen++;cost+=t.fee;hole+=t.holes;hh+=t.handle_holes;}
    std::cout<<std::setprecision(12)<<"{\"M\":"<<m<<",\"G\":"<<g<<",\"mapping\":"<<map<<",\"pairs\":"<<pairs<<",\"near_pairs\":"<<near_pairs<<",\"triangles\":"<<triangles<<",\"triples_union42\":"<<triples<<",\"triples_union38\":"<<near_triples<<",\"chosen\":"<<chosen<<",\"mean_union\":"<<(triples?mean_union/triples:0)<<",\"chosen_union\":"<<(chosen?hole/chosen:0)<<",\"chosen_handles\":"<<(chosen?hh/chosen:0)<<",\"chosen_generic_lower\":"<<(chosen?cost/(3*chosen):0)<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
