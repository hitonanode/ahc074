#define BARCODE_PAIR_REPLACE_RATE 0
// Ported from other_agents/gpt6pro-07-barcode_solution_and_tests.zip (barcode_solution.cpp): <bits/stdc++.h> replaced by
// individual headers, stderr statistics printed as `name = value` lines.
// Layered Barcode Display / AHC074 — improved standalone C++20 solution.
// Based on the exact program supplied by the user.
// Additions: matching-edge replacement, two-direction generic cost estimation,
// equivalent-plan elimination, flexible final-order postprocessing, and a
// two-deletions/one-repair move neighborhood. Generic sheets may remain
// interleaved at the end of a request; cleanup restores their contiguous block.
// Requests are read strictly online, one at a time. Every response is flushed.
// Compile: g++ -std=c++20 -O2 -DNDEBUG barcode_solution.cpp -o solution
// Default design: M=6, G=36, map=2400, assignment=2000000 iterations, 1.0s cap.
// CPU fallback threshold: 1.55s. All heuristic paths check visibility/display.
// BARCODE_FORCE_FAST_ON_SPLIT and BARCODE_FORCE_FALLBACK are validation switches.

#ifndef BARCODE_RELAX_GENERIC
#define BARCODE_RELAX_GENERIC 1
#endif
#ifndef BARCODE_SYMMETRIC_ESTIMATE
#define BARCODE_SYMMETRIC_ESTIMATE 1
#endif
#ifndef BARCODE_DESIGN_ITERS
#define BARCODE_DESIGN_ITERS 2000000
#endif
#ifndef BARCODE_DESIGN_SECONDS
#define BARCODE_DESIGN_SECONDS 1.0
#endif
#ifndef BARCODE_FAST_THRESHOLD
#define BARCODE_FAST_THRESHOLD 1.55
#endif
// Candidate: original source + cardinality-preserving matching-edge replacement.
// Existing pair (a,b) and two singleton sheets c,d can become pair (c,d)
// and singleton sheets a,b. All changed columns and hole counts use the
// original exact incremental objective. No online operations are changed.
#ifndef BARCODE_PAIR_REPLACE_RATE
#define BARCODE_PAIR_REPLACE_RATE 100
#endif
#ifndef BARCODE_PAIR_COL_REPAIR
#define BARCODE_PAIR_COL_REPAIR 1
#endif
// Original program supplied by the user; Markdown escapes normalized.
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

// Behavioral transcription of the original program supplied by the user.
// Only duplicate include lists / comments and message escaping are normalized.
class Comparator {
public:
    using u64 = std::uint64_t;
    int M = 0, G = 0;
    bool complete = false;
    std::vector<std::pair<int, int>> edge;
    std::vector<int> polarity;
    std::vector<u64> opq, black;

    template<class RNG>
    void init(int m, int g, RNG& rng) {
        M = m; G = g;
        std::vector<std::pair<int, int>> all;
        for (int a = 0; a < M; ++a)
            for (int b = a + 1; b < M; ++b) all.emplace_back(a, b);
        std::shuffle(all.begin(), all.end(), rng);
        edge.resize(G); polarity.resize(G);
        for (int j = 0; j < G; ++j) {
            edge[j] = all[j % all.size()];
            polarity[j] = int(rng() & 1);
        }
        rebuild();
    }

    void reset(int m, int g, const std::vector<std::pair<int, int>>& e,
               const std::vector<int>& p) {
        M = m; G = g; edge = e; polarity = p;
        rebuild();
    }

    void rebuild() {
        assert(1 < M && M <= 12 && 0 < G && G <= 64);
        assert(int(edge.size()) == G && int(polarity.size()) == G);
        opq.assign(M, 0); black.assign(M, 0);
        std::array<unsigned, 12> adj{};
        for (int j = 0; j < G; ++j) {
            auto [a, b] = edge[j];
            assert(a != b && 0 <= a && a < M && 0 <= b && b < M);
            u64 bit = u64(1) << j;
            opq[a] |= bit; opq[b] |= bit;
            black[polarity[j] ? a : b] |= bit;
            adj[a] |= 1U << b; adj[b] |= 1U << a;
        }
        complete = true;
        for (int i = 0; i < M; ++i)
            complete &= (adj[i] | (1U << i)) == (1U << M) - 1;
    }

    std::array<unsigned, 12> closure(u64 target, u64 holes) const {
        std::array<unsigned, 12> reach{};
        holes &= G == 64 ? ~u64(0) : (u64(1) << G) - 1;
        while (holes) {
            int j = __builtin_ctzll(holes);
            holes &= holes - 1;
            auto [a, b] = edge[j];
            if (int((target >> j) & 1) != polarity[j]) std::swap(a, b);
            reach[a] |= 1U << b;
        }
        for (int k = 0; k < M; ++k)
            for (int a = 0; a < M; ++a)
                if ((reach[a] >> k) & 1) reach[a] |= reach[k];
        return reach;
    }

    bool compatible(u64 a, u64 b) const {
        auto reach = closure(a, a ^ b);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return false;
        return true;
    }

    std::vector<std::pair<int, int>> plan(const std::vector<int>& current,
                                         u64 target, u64 holes) const {
        if (!complete || int(current.size()) != M) return {{-1, -1}};
        auto reach = closure(target, holes);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return {{-1, -1}};
        bool satisfied = true;
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) satisfied = false;
        if (satisfied) return {};

        std::array<unsigned, 12> conflict{};
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) {
                    conflict[current[i]] |= 1U << current[j];
                    conflict[current[j]] |= 1U << current[i];
                }

        std::array<unsigned char, 1 << 12> valid{};
        valid[0] = 1;
        unsigned kept = 0;
        int best_count = -1, witness = -1;
        const int bottom = current.back();
        const unsigned bottom_bit = 1U << bottom;
        const unsigned end = 1U << M;
        for (unsigned mask = 1; mask < end; ++mask) {
            unsigned rest = mask & (mask - 1);
            int a = __builtin_ctz(mask);
            valid[mask] = valid[rest] && !(rest & conflict[a]);
            if (!valid[mask]) continue;
            int count = __builtin_popcount(mask);
            if (count <= best_count) continue;
            bool legal = mask & bottom_bit;
            int w = -1;
            if (!legal) {
                for (int b = 0; b < M; ++b) {
                    if ((mask >> b & 1) || b == bottom) continue;
                    if (!(reach[b] & (mask | bottom_bit))) {
                        w = b; legal = true; break;
                    }
                }
            }
            if (legal) { kept = mask; best_count = count; witness = w; }
        }
        if (best_count < 0) return {{-1, -1}};

        auto required = reach;
        int last = -1;
        for (int a : current) if (kept >> a & 1) {
            if (last >= 0) required[last] |= 1U << a;
            last = a;
        }
        if (witness >= 0) {
            required[last] |= 1U << witness;
            required[bottom] |= 1U << witness;
        }
        std::array<unsigned, 12> pred{};
        for (int a = 0; a < M; ++a)
            for (int b = 0; b < M; ++b)
                if (required[a] >> b & 1) pred[b] |= 1U << a;

        std::vector<int> goal;
        unsigned placed = 0;
        for (int step = 0; step < M; ++step) {
            int next = -1;
            for (int a : current)
                if (!(placed >> a & 1) && !(pred[a] & ~placed)) { next = a; break; }
            if (next < 0) return {{-1, -1}};
            goal.push_back(next);
            placed |= 1U << next;
        }

        std::vector<int> order = current;
        std::vector<std::pair<int, int>> moves;
        for (int a : current) if (!(kept >> a & 1)) {
            u64 covered = 0;
            bool visible = false;
            for (int b : order) {
                if (b == a) { visible = (opq[a] & ~covered) != 0; break; }
                covered |= opq[b];
            }
            if (!visible) return {{-1, -1}};
            int successor = -1;
            bool passed = false;
            for (int b : goal) {
                if (passed && (kept >> b & 1)) { successor = b; break; }
                if (b == a) passed = true;
            }
            int old = int(std::find(order.begin(), order.end(), a) - order.begin());
            order.erase(order.begin() + old);
            int depth = successor < 0 ? M - 1
                : int(std::find(order.begin(), order.end(), successor) - order.begin());
            order.insert(order.begin() + depth, a);
            if (old != depth) moves.emplace_back(a, depth);
            kept |= 1U << a;
        }
        if (order != goal) return {{-1, -1}};
        return moves;
    }
};

namespace comparison_windows {
using U = std::uint64_t;
struct Rng {
    U x = 0x71eb2566be932e31ULL;
    U operator()() { x ^= x << 7; x ^= x >> 9; return x; }
    int operator()(int n) { return int((*this)()%n); }
    double real() { return ((*this)()>>11)*0x1.0p-53; }
};
inline U closure8(U r,int m) {
    for(int k=0;k<m;k++)r|=((r>>k)&0x0101010101010101ULL)*((r>>(8*k))&255);
    return r;
}
struct MapStats {
    int iterations=0,accepted=0,pairs=0,window_swaps=0;
    double old_score=0,new_score=0;
};
inline MapStats optimize_map(std::vector<U>& A,int m,int g,
    std::vector<std::pair<int,int>>& edges,std::vector<int>& polarity,
    std::vector<int>& permutation,double seconds=0.2,int fixed_iters=0,
    int cutoff=28,double strength=0.7,double generic_weight=1.0,
    double closure_penalty=0.0,double window_rate=0.30)
{
    MapStats stats;
    if(m>8||m<2||g>=64||g<m*(m-1)/2)return stats;
    const auto start=std::chrono::steady_clock::now();
    Rng rng;const int n=int(A.size());
    std::vector<std::pair<int,int>> ep;
    int index[8][8];std::memset(index,-1,sizeof(index));
    for(int a=0;a<m;a++)for(int b=a+1;b<m;b++){
        index[a][b]=index[b][a]=int(ep.size());ep.push_back({a,b});
    }
    int ne=int(ep.size());
    std::vector<U> mask(ne),fwd(ne),rev(ne);
    std::vector<int> which(64,-1),counts(ne),order(64);
    std::iota(order.begin(),order.end(),0);
    U pol=0;
    for(int e=0;e<ne;e++){auto[a,b]=ep[e];fwd[e]=1ULL<<(8*a+b);rev[e]=1ULL<<(8*b+a);}
    for(int j=0;j<g;j++){
        auto[a,b]=edges[j];int e=index[a][b];which[j]=e;mask[e]|=1ULL<<j;counts[e]++;
        int c=polarity[j];if(a>b)c^=1;if(c)pol|=1ULL<<j;
    }
    for(int c:counts)if(!c)return stats;
    struct Pair {U au,diff,dir;int u,v;double base,w;};
    std::vector<Pair> pairs;
    std::vector<double> degree(n);
    double factor[65];for(int c=0;c<=64;c++)factor[c]=std::exp(-closure_penalty*(c-20));
    double bfactor[3];for(int d=-1;d<=1;d++)bfactor[d+1]=std::exp(0.35*(1-generic_weight)*d);
    double center=24*(1-(1-generic_weight)*g/64.0);
    for(int u=0;u<n;u++)for(int v=u+1;v<n;v++){
        U d=A[u]^A[v];int h=__builtin_popcountll(d);if(h>cutoff)continue;
        U r=0,z=A[u]^pol;
        for(int e=0;e<ne;e++){U q=d&mask[e];if(q&~z)r|=fwd[e];if(q&z)r|=rev[e];}
        U cl=closure8(r,m);bool ok=!(cl&0x8040201008040201ULL);
        int hg=__builtin_popcountll(d&((1ULL<<g)-1));
        double base=std::exp((center-h+(1-generic_weight)*hg)*0.35);
        double w=ok?base*factor[__builtin_popcountll(cl)]:0;
        pairs.push_back({A[u],d,r,u,v,base,w});degree[u]+=w;degree[v]+=w;
    }
    stats.pairs=int(pairs.size());
    auto value=[&](double d){return std::pow(d+0.2,strength);};
    auto objective=[&](){double s=0;for(double d:degree)s+=value(d);return s;};
    double score=objective(),best=score;stats.old_score=score;
    auto best_mask=mask;auto best_order=order;U best_pol=pol;
    int np=int(pairs.size());
    std::vector<U> ndir(np);
    std::vector<double> nbase(np),nw(np),delta(n);
    std::vector<int>changed;changed.reserve(np);
    double elapsed=0;
    for(int it=0;;it++){
        if((it&15)==0){
            elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            if(elapsed>=seconds || (fixed_iters>0 && it>=fixed_iters))break;
        }
        stats.iterations++;
        double progress=fixed_iters?double(it)/fixed_iters:elapsed/seconds;
        int ia=rng(g),ib=rng(g),a=order[ia],b=order[ib];
        bool swindow=rng.real()<window_rate;
        if(swindow){ib=g+rng(64-g);b=order[ib];}
        int kind=rng(10),ea=which[a],eb=swindow?ea:which[b];
        U olda=mask[ea],oldb=mask[eb],oldpol=pol,affected=0;
        int transfer=-1;
        if(swindow){
            mask[ea]^=(1ULL<<a)|(1ULL<<b);
            pol=(pol&~(1ULL<<b))|(((oldpol>>a)&1)<<b);
            affected=(1ULL<<a)|(1ULL<<b);
        }else if(kind<3){pol^=1ULL<<a;affected=1ULL<<a;eb=ea;oldb=olda;}
        else if(kind<8){
            if(ea==eb)continue;
            mask[ea]^=(1ULL<<a)|(1ULL<<b);mask[eb]^=(1ULL<<a)|(1ULL<<b);
            affected=(1ULL<<a)|(1ULL<<b);
        }else{
            if(counts[ea]<2)continue;
            eb=rng(ne);if(ea==eb)continue;
            oldb=mask[eb];mask[ea]^=1ULL<<a;mask[eb]|=1ULL<<a;
            transfer=eb;affected=1ULL<<a;
        }
        U erase=fwd[ea]|rev[ea]|fwd[eb]|rev[eb];
        std::fill(delta.begin(),delta.end(),0);changed.clear();
        for(int p=0;p<np;p++){
            auto&q=pairs[p];if(!(q.diff&affected))continue;
            U r=q.dir&~erase,z=q.au^pol;
            U d=q.diff&mask[ea];if(d&~z)r|=fwd[ea];if(d&z)r|=rev[ea];
            d=q.diff&mask[eb];if(d&~z)r|=fwd[eb];if(d&z)r|=rev[eb];
            double base=q.base;
            if(swindow){int dh=int((q.diff>>b)&1)-int((q.diff>>a)&1);base*=bfactor[dh+1];}
            if(r==q.dir&&base==q.base)continue;
            U cl=closure8(r,m);bool ok=!(cl&0x8040201008040201ULL);
            double w=ok?base*factor[__builtin_popcountll(cl)]:0;
            ndir[p]=r;nbase[p]=base;nw[p]=w;changed.push_back(p);
            double dw=w-q.w;delta[q.u]+=dw;delta[q.v]+=dw;
        }
        double ds=0;
        for(int u=0;u<n;u++)if(std::abs(delta[u])>1e-9)
            ds+=value(std::max(0.0,degree[u]+delta[u]))-value(degree[u]);
        double temp=0.2*std::pow(0.005/0.2,progress);
        if(ds>=0||rng.real()<std::exp(ds/temp)){
            stats.accepted++;score+=ds;
            for(int p:changed){pairs[p].dir=ndir[p];pairs[p].base=nbase[p];pairs[p].w=nw[p];}
            for(int u=0;u<n;u++)degree[u]=std::max(0.0,degree[u]+delta[u]);
            if(swindow){
                stats.window_swaps++;which[a]=-1;which[b]=ea;std::swap(order[ia],order[ib]);
            }else{
                if(kind>=3&&kind<8)std::swap(which[a],which[b]);
                if(transfer>=0){counts[ea]--;counts[eb]++;which[a]=eb;}
            }
            if(score>best){best=score;best_mask=mask;best_pol=pol;best_order=order;}
        }else{mask[ea]=olda;mask[eb]=oldb;pol=oldpol;}
    }
    for(int j=0;j<g;j++){
        int x=best_order[j],e=0;while(e<ne&&!(best_mask[e]>>x&1))e++;
        assert(e<ne);edges[j]=ep[e];polarity[j]=(best_pol>>x)&1;
    }
    if(permutation.empty()){permutation.resize(64);std::iota(permutation.begin(),permutation.end(),0);}
    auto oldperm=permutation;
    for(int j=0;j<64;j++)permutation[j]=oldperm[best_order[j]];
    for(U&a:A){U b=0;for(int j=0;j<64;j++)b|=((a>>best_order[j])&1)<<j;a=b;}
    stats.new_score=best;
    return stats;
}
} // namespace comparison_windows

struct PaperDesign {
    using U64 = uint64_t;
    struct Unit { int a=-1,b=-1,c=-1; };
    struct RNG {
        U64 x;
        explicit RNG(U64 s=0x6176abcd1349ULL):x(s){}
        U64 next(){ x^=x<<7; x^=x>>9; return x; }
        int operator()(int n){return ((unsigned __int128)next()*unsigned(n))>>64;}
        double real(){return (next()>>11)*0x1.0p-53;}
    } rng;
    int M,G,H,U,need;
    std::vector<U64> A,hb;
    std::vector<int> handle,owner;
    std::vector<Unit> unit;
    std::vector<std::vector<int>> partners;
    std::array<std::array<uint8_t,256>,256> ok{};
    std::array<std::array<float,256>,256> gcost{};
    std::vector<int> nc,nt,n1,pairOne;
    std::vector<std::array<int,2>> hn;
    double cur=0;
    double holeWeight=0.50, digWeight=1.0;
    double rankPriority=0.85;
    bool guardDesign=false;
    int iterations=0;
    int edgeReplaceAttempts=0,edgeReplaceAccepted=0;
    int fillerIterations=0,fillerAccepted=0;
    double fillerProxyBefore=0,fillerProxyAfter=0;

    static U64 low(int n){return n==64?~U64(0):(U64(1)<<n)-1;}
    static int pc(U64 x){return __builtin_popcountll(x);}
    PaperDesign(const std::vector<U64>& a,int m,int g):M(m),G(g),H(64-g),U(192-m),need(256-U),A(a){
        handle.resize(H);std::iota(handle.begin(),handle.end(),G);
        hb.resize(256);for(int i=0;i<256;i++)hb[i]=A[i]>>G;
        owner.assign(256,-1); partners.resize(256);
        nc.resize(H);nt.resize(H);n1.resize(H);pairOne.resize(H);hn.resize(H);
    }
    bool valid(const Unit& u,int c)const{
        return u.b<0 || (((hb[u.a]^hb[u.b])>>c)&1)==0;
    }
    int color(const Unit& u,int c)const{return hb[u.a]>>c&1;}
    int weight(const Unit& u)const{return u.b<0?1:2;}
    U64 holes(const Unit& u)const{
        U64 d=u.b<0?0:hb[u.a]^hb[u.b];
        return (low(H)&~low(u.c+1))|d;
    }
    double colcost(int c)const{
        int imb=std::max(0,std::abs(nc[c]-2*n1[c])-1);
        int p=nt[c]-nc[c],p1=pairOne[c],p0=p-p1;
        double base=nt[c]*(nc[c]-1)*0.5;
        int firstPair=n1[c]>nc[c]-n1[c]?p1:n1[c]<nc[c]-n1[c]?p0:std::max(p0,p1);
        double alt=nc[c]*(nc[c]-1)*0.5+p0*p0+p1*p1-firstPair;
        if(guardDesign){
            int q=nc[c]-p;
            alt=base-0.5*p*q;
            if((p0==0||p1==0)&&p>0)alt+=p-1;
        }
        double retrieval=base-rankPriority*std::max(0.0,base-alt);
        return digWeight*retrieval+(guardDesign?0.0:5.0*imb*imb)+
            ((n1[c]==0 || n1[c]==nc[c])?100000.0:0.0);
    }
    double hcost(int j)const{
        static const std::array<double,257*257> table=[](){
            std::array<double,257*257> a{};
            for(int x=0;x<=256;x++)for(int y=0;y<=256;y++)
                if(x+y)a[x*257+y]=4.0*x*y/(x+y);
            return a;
        }();
        return holeWeight*table[hn[j][0]*257+hn[j][1]];
    }
    double gc(const Unit& u)const{return u.b<0?0:gcost[u.a][u.b]*2;}
    void update(const Unit& u,int sgn){
        cur-=colcost(u.c);nc[u.c]+=sgn;nt[u.c]+=sgn*weight(u);n1[u.c]+=sgn*color(u,u.c);
        if(u.b>=0)pairOne[u.c]+=sgn*color(u,u.c);
        cur+=colcost(u.c);
        U64 hs=holes(u);
        for(U64 s=hs;s;s&=s-1){
            int j=__builtin_ctzll(s);cur-=hcost(j);
            hn[j][hb[u.a]>>j&1]+=sgn;
            if(u.b>=0)hn[j][hb[u.b]>>j&1]+=sgn;
            cur+=hcost(j);
        }
        cur+=sgn*gc(u);
    }
    void rebuild(){
        std::fill(nc.begin(),nc.end(),0);std::fill(nt.begin(),nt.end(),0);std::fill(n1.begin(),n1.end(),0);
        std::fill(pairOne.begin(),pairOne.end(),0);
        std::fill(hn.begin(),hn.end(),std::array<int,2>{0,0});
        cur=0;for(int j=0;j<H;j++)cur+=colcost(j);
        for(const auto& u:unit)update(u,1);
        for(int x=0;x<U;x++){owner[unit[x].a]=x;if(unit[x].b>=0)owner[unit[x].b]=x;}
    }
    template<class Compatible,class Estimate,class Expired>
    bool initialize(Compatible compatible,Estimate estimate,Expired expired){
        struct E{double w;int a,b;};std::vector<E> edges;
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){
            if((b&31)==0 && expired())return false;
            if(!compatible(A[a],A[b]))continue;
            ok[a][b]=ok[b][a]=1;
            partners[a].push_back(b);partners[b].push_back(a);
            U64 d=A[a]^A[b];
            gcost[a][b]=gcost[b][a]=estimate(A[a],A[b]);
            edges.push_back({0.65*pc(d>>G)+2*gcost[a][b]+0.04*pc(d),a,b});
        }
        std::sort(edges.begin(),edges.end(),[](const E&a,const E&b){return a.w<b.w;});
        std::vector<char> used(256,0);
        for(const auto& e:edges){
            if(int(unit.size())==need)break;
            if(used[e.a]||used[e.b])continue;
            used[e.a]=used[e.b]=1;unit.push_back({e.a,e.b,-1});
        }
        auto edgeCost=[&](int a,int b){U64 d=A[a]^A[b];return 0.65*pc(d>>G)+2*gcost[a][b]+0.04*pc(d);};
        while(int(unit.size())<need){
            double best=1e100;int bx=-1,bu=-1,bv=-1,flip=0;
            for(int x=0;x<int(unit.size());x++)for(int f=0;f<2;f++){
                if(expired())return false;
                int a=f?unit[x].b:unit[x].a,b=f?unit[x].a:unit[x].b;
                for(int u:partners[a])if(!used[u])for(int v:partners[b])if(!used[v]&&u!=v){
                    double c=edgeCost(a,u)+edgeCost(b,v)-edgeCost(a,b);
                    if(c<best){best=c;bx=x;bu=u;bv=v;flip=f;}
                }
            }
            if(bx<0)break;
            int a=flip?unit[bx].b:unit[bx].a,b=flip?unit[bx].a:unit[bx].b;
            unit[bx]={a,bu,-1};unit.push_back({b,bv,-1});used[bu]=used[bv]=1;
        }
        if(int(unit.size())<need)return false;
        for(int a=0;a<256;a++)if(!used[a])unit.push_back({a,-1,-1});
        std::vector<int> perm(U);std::iota(perm.begin(),perm.end(),0);
        for(int i=U-1;i>0;i--)std::swap(perm[i],perm[rng(i+1)]);
        auto take=[&](int c,int colorWanted,bool pairFirst){
            for(int pass=0;pass<2;pass++)for(int x:perm){
                auto& u=unit[x];if(u.c>=0||(u.b>=0)!=(pairFirst^(pass!=0))||!valid(u,c)||color(u,c)!=colorWanted)continue;
                u.c=c;nc[c]++;n1[c]+=colorWanted;return true;
            }
            return false;
        };
        for(int c=0;c<H;c++)for(int v=0;v<2;v++)if(!take(c,v,false))return false;
        std::vector<int> cap(H,2);int tot=H*2;
        while(tot+2<=U){
            int best=0;double val=1e100;
            for(int c=0;c<H;c++){
                double q=(cap[c]+1.0)/(c+1.5);if(q<val)val=q,best=c;
            }
            cap[best]+=2;tot+=2;
        }
        for(int c=H-1;c>=0;c--)while(nc[c]<cap[c]){
            int v=2*n1[c]<nc[c]?1:0;
            if(!take(c,v,true)&&!take(c,v^1,true))break;
        }
        for(auto& u:unit)if(u.c<0){
            int best=-1;double cost=1e100;
            for(int c=0;c<H;c++)if(valid(u,c)){
                double q=weight(u)*(nc[c]*0.5+0.5*(H-1-c))+nc[c]*0.5+
                    3*std::abs(nc[c]+1-2*(n1[c]+color(u,c)));
                if(q<cost)cost=q,best=c;
            }
            if(best<0)return false;
            u.c=best;nc[best]++;n1[best]+=color(u,best);
        }
        rebuild();return true;
    }
    void anneal(double seconds,int fixedIterations=0){
        auto start=std::chrono::steady_clock::now();
        double progress=0,temp=2.0;
        static std::array<double,16384> logs=[](){std::array<double,16384>a{};for(int i=0;i<16384;i++)a[i]=-std::log((i+0.5)/16384);return a;}();
        auto accept=[&](double d){return d<=0||d<temp*logs[rng.next()&16383];};
        std::vector<Unit> best=unit;std::vector<int> bestHandle=handle;
        double bestCost=cur;
        // The original annealing moves never change whether a slot is paired.
        // The new move preserves that invariant, so these slot lists stay valid.
        std::vector<int> pairSlots,singleSlots;
        for(int x=0;x<U;x++)(unit[x].b<0?singleSlots:pairSlots).push_back(x);
        auto replace_edge=[&](){
            if(pairSlots.empty()||singleSlots.size()<2)return;
            int x=pairSlots[rng(pairSlots.size())];
            int y=singleSlots[rng(singleSlots.size())];
            const auto& ps=partners[unit[y].a];
            if(ps.empty())return;
            int z=-1;
            for(int tries=0;tries<4;tries++){
                int candidate=owner[ps[rng(ps.size())]];
                if(candidate!=y&&unit[candidate].b<0){z=candidate;break;}
            }
            if(z<0)return;
            edgeReplaceAttempts++;
            Unit ox=unit[x],oy=unit[y],oz=unit[z];
            Unit nx{oy.a,oz.a,ox.c},ny{ox.a,-1,oy.c},nz{ox.b,-1,oz.c};
            if(rng(2))std::swap(ny.a,nz.a);
#if BARCODE_PAIR_COL_REPAIR
            // Reassign the new pair to a compatible column among the three
            // available slots. Swapping columns retains the column sizes.
            std::array<int,3> columns{nx.c,ny.c,nz.c};
            std::array<int,3> choices{};int choicesCount=0;
            for(int i=0;i<3;i++)if(valid(nx,columns[i]))choices[choicesCount++]=i;
            if(!choicesCount)return;
            int chosen=choices[rng(choicesCount)];
            if(chosen==1)std::swap(nx.c,ny.c);
            if(chosen==2)std::swap(nx.c,nz.c);
#else
            if(!valid(nx,nx.c))return;
#endif
            double old=cur;
            update(ox,-1);update(oy,-1);update(oz,-1);
            update(nx,1);update(ny,1);update(nz,1);
            if(accept(cur-old)){
                edgeReplaceAccepted++;
                unit[x]=nx;unit[y]=ny;unit[z]=nz;
                owner[nx.a]=owner[nx.b]=x;owner[ny.a]=y;owner[nz.a]=z;
            }else{
                update(nx,-1);update(ny,-1);update(nz,-1);
                update(ox,1);update(oy,1);update(oz,1);cur=old;
            }
        };
        auto mutate=[&](int x,int y,Unit nx,Unit ny){
            if(!valid(nx,nx.c)||!valid(ny,ny.c))return;
            if((nx.b>=0&&!ok[nx.a][nx.b])||(ny.b>=0&&!ok[ny.a][ny.b]))return;
            Unit ox=unit[x],oy=unit[y];double old=cur;
            update(ox,-1);update(oy,-1);update(nx,1);update(ny,1);
            if(accept(cur-old)){
                unit[x]=nx;unit[y]=ny;
                owner[nx.a]=x;if(nx.b>=0)owner[nx.b]=x;
                owner[ny.a]=y;if(ny.b>=0)owner[ny.b]=y;
            }else{update(nx,-1);update(ny,-1);update(ox,1);update(oy,1);cur=old;}
        };
        for(int it=0;;it++){
            iterations=it;
            if((it&255)==0){
                double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
                progress=fixedIterations>0?double(it)/fixedIterations:elapsed/seconds;
                if(progress>=1 || elapsed>=seconds)break;
                temp=2.0*std::pow(0.015/2.0,progress);
            }
            int type=rng(1000);
            if(type<5){
                int a=rng(H),b=rng(H);if(a==b)continue;
                bool validSwap=true;
                for(const auto& u:unit)if(u.b>=0&&(u.c==a||u.c==b)){
                    int j=u.c==a?b:a;
                    if((hb[u.a]^hb[u.b])>>j&1){validSwap=false;break;}
                }
                if(!validSwap)continue;
                double old=cur;
                auto sw=[&](){std::swap(handle[a],handle[b]);for(auto& h:hb)if(((h>>a)^(h>>b))&1)h^=(U64(1)<<a)|(U64(1)<<b);};
                sw();rebuild();
                if(!accept(cur-old)){sw();rebuild();}
            }else if(type<5+BARCODE_PAIR_REPLACE_RATE){
                replace_edge();
            }else{
                int x=rng(U),y=rng(U);if(x==y)continue;
                Unit nx=unit[x],ny=unit[y];
                if(type<430){
                    if(nx.b<0){std::swap(x,y);nx=unit[x];ny=unit[y];if(nx.b<0)continue;}
                    int ix=rng(2),iy=ny.b<0?0:rng(2);
                    if(type<380){
                        int fixed=ix==0?nx.b:nx.a;
                        const auto& p=partners[fixed];if(p.empty())continue;
                        int newTarget=p[rng(p.size())];y=owner[newTarget];
                        if(x==y)continue;
                        ny=unit[y];iy=ny.a==newTarget?0:1;
                    }
                    int& a=ix==0?nx.a:nx.b;int& b=iy==0?ny.a:ny.b;std::swap(a,b);
                }else if(type<750){
                    if(nx.c==ny.c)continue;
                    std::swap(nx.c,ny.c);
                }else if(type<900){
                    if(nx.c==ny.c||nc[nx.c]<=2)continue;
                    nx.c=ny.c;
                }else{
                    int c=nx.c,d=ny.c;if(c==d||nc[c]<=2)continue;
                    int z=-1;
                    for(int t=0;t<16;t++){int j=rng(U);if(j!=x&&unit[j].c==c&&color(unit[j],c)!=color(nx,c)){z=j;break;}}
                    if(z<0)continue;
                    y=z;ny=unit[y];nx.c=ny.c=d;
                }
                mutate(x,y,nx,ny);
            }
            if(cur<bestCost-1e-7){bestCost=cur;best=unit;bestHandle=handle;}
        }
        unit=best;handle=bestHandle;
        for(int i=0;i<256;i++){hb[i]=0;for(int j=0;j<H;j++)hb[i]|=((A[i]>>handle[j])&1)<<j;}
        rebuild();
    }
    std::vector<double> hole_probabilities()const{
        std::vector<double> p(H,0.5);for(int j=0;j<H;j++)if(hn[j][0]+hn[j][1])p[j]=double(hn[j][1])/(hn[j][0]+hn[j][1]);return p;
    }

};

using u64 = std::uint64_t;
namespace {
constexpr int N=64,K=192,P=256;

struct Paper {u64 opaque=0,black=0;};
struct Block {u64 mask=0,y=0;int pf=-1;};
struct Solver {
    int M=6,G=36,H=28;
    Comparator comparator;
    int comparison_target=-1;
    u64 comparison_holes=0;
    std::vector<u64>A;
    std::vector<int>handle,hidx;
    u64 gmask=0,hmask=0;
    std::vector<Block>blocks;
    std::vector<int>flip_cov;
    std::vector<Paper>paper;
    std::vector<u64>h_opq,h_blk;
    std::vector<int>col_of,block_of,ded;
    int base_paper=0;
    std::vector<int>bias_c;
    std::vector<double>bias_g;
    std::vector<std::array<int,2>>units;
    std::vector<std::array<std::vector<int>,2>>members;
    std::vector<int>order;
    int top_d=-1,top_pred=-1;
    struct Filler {int paper,pred;int lvl=0,hi=0;};
    std::vector<Filler>fillers;
    std::vector<std::pair<int,int>>ops;
    explicit Solver(std::vector<u64>a):A(std::move(a)){}
    std::pair<int,int>touch(u64 au,u64 diff)const{
        int t=0,bad=0;
        for(const auto&b:blocks){u64 d=diff&b.mask;if(!d)continue;t++;u64 x=(au^b.y)&d;if(x!=0&&x!=d)bad++;}
        return{t,bad};
    }
    std::array<int,3>pair_codes(int u,int v)const{
        u64 diff=A[u]^A[v];int cu=0,cv=0,bad=0,pw=1;
        for(const auto&b:blocks){
            u64 d=diff&b.mask;
            if(d){u64 x=(A[u]^b.y)&d;if(x!=0&&x!=d)bad++;int on=__builtin_popcountll(x)*2>__builtin_popcountll(d);cu+=pw*(on+1);cv+=pw*(2-on);}
            pw*=3;
        }
        return{cu,cv,bad};
    }
    int color_at(int x,int l)const{
        auto[u,v]=units[x];int c=A[u]>>handle[l]&1;
        if(v>=0&&(int)(A[v]>>handle[l]&1)!=c)return-1;
        return c;
    }
    std::vector<int>unit_columns()const{
        std::vector<int>col(units.size(),-1);
        for(int l=0;l<H;l++)for(int c=0;c<2;c++)for(int x:members[l][c])col[x]=l;
        return col;
    }
    u64 handle_bits(u64 windows)const{
        u64 r=0;for(int j=0;j<H;j++)r|=(windows>>handle[j]&1)<<j;return r;
    }
    void set_members(const std::vector<int>&col){
        for(int l=0;l<H;l++)members[l][0].clear(),members[l][1].clear();
        for(int x=0;x<(int)units.size();x++)if(col[x]>=0)members[col[x]][color_at(x,col[x])].push_back(x);
    }

    std::vector<int> wanted_blocks(int u,u64 holes) {
        comparison_target=u;
        comparison_holes=holes&gmask;
        return {};
    }
    void set_blocks(const std::vector<int>&) {
        if(!comparison_holes)return;
        int offset=-1;
        for(int i=0;i<K;i++)if(block_of[order[i]]>=0){offset=i;break;}
        if(offset<0||offset+M>K){invalid=true;return;}
        std::vector<int> local;
        for(int i=0;i<M;i++){
            int k=order[offset+i];
            if(k<0||k>=M){invalid=true;return;}
            local.push_back(k);
        }
        auto path=comparator.plan(local,A[comparison_target],comparison_holes);
        for(auto [k,d]:path){
            if(k<0||k>=M||d<0||d>=M){invalid=true;return;}
            move(k,offset+d);
            if(invalid)return;
        }
    }
  int adaptive_request = -1;
  bool adaptive_initialized = false;
  std::vector<double> adaptive_weights;
  std::vector<std::array<double,2>> adaptive_holes;
  double adaptive_rank = 1.0, adaptive_future = 1.0, adaptive_top_penalty = 0.35;
  double adaptive_end_weight = 0.6;
  bool fast_mode = false;
  long long fast_requests = 0;
  long long adaptive_failures = 0;
  // These flags record whether changing an option actually changes an insertion.
  // Equivalent candidates may be skipped only after all affected calls agree.
  enum : unsigned { kRetSensitive=1, kFretSensitive=2, kFretRetSensitive=4 };
  bool check_equivalence = false;
  unsigned equivalence_sensitive = 0;
  long long evaluated_candidates = 0, duplicate_candidates = 0;
  void init_adaptive() {
      if (adaptive_initialized) return;
      adaptive_initialized = true;
      adaptive_weights.assign(K,0.0);
      adaptive_holes.assign(H,{0.0,0.0});
      for (int u=0;u<P;u++) {
          int d=ded[u];
          if (d<0) continue;
          adaptive_weights[d] += 1.0;
          for (int c=0;c<H;c++) if (!(paper[d].opaque >> handle[c] & 1))
              adaptive_holes[c][A[u] >> handle[c] & 1] += 1.0/P;
      }
  }
  double adaptive_next_cost() const {
      std::vector<int> rank(H,0);
      std::vector<std::array<int,2>> first(H);
      std::vector<std::array<bool,2>> available(H,{false,false});
      for(auto& f:first)f={-1,-1};
      double cost=0;
      for(int k:order) {
          int c=col_of[k];if(c<0)continue;
          int color=paper[k].black >> handle[c] & 1;
          if(k==top_d || is_filler(k)) {available[c][color]=true;continue;}
          if(first[c][color]<0)first[c][color]=rank[c];
          cost+=adaptive_weights[k]*rank[c]/P;
          rank[c]++;
      }
      for(int c=0;c<H;c++)for(int color=0;color<2;color++) {
          int fixes=available[c][color]?0:first[c][color];
          if(fixes<0)fixes=rank[c];
          cost+=adaptive_holes[c][color]*fixes;
      }
      return cost;
  }
  void adaptive_insert(int x,int u,int barrier=-1,int mode=2,unsigned option_bit=0) {
      const int c=col_of[x],cx=paper[x].black >> handle[c] & 1;
      std::vector<int> v;
      for (int k:order) if (k!=x && in_column(k,c)) v.push_back(k);
      const int n=v.size();
      int lo=0;
      if (barrier>=0) {
          auto it=std::find(v.begin(),v.end(),barrier);
          if (it==v.end()) { invalid=true; return; }
          lo=int(it-v.begin())+1;
      }
      std::vector<double> suffix(n+1,0.0);
      std::array<int,2> first={n,n};
      for (int i=n-1;i>=0;i--) {
          suffix[i]=suffix[i+1]+adaptive_weights[v[i]];
          first[paper[v[i]].black >> handle[c] & 1]=i;
      }
      int requested=u>=0?ded[u]:-1;
      bool need=requested>=0 && c!=col_of[requested] && !(paper[requested].opaque >> handle[c] & 1);
      int desired=u>=0?(A[u] >> handle[c] & 1):0;
      double best=1e100;int gap=n;
      const bool compare_modes = check_equivalence && option_bit && !(equivalence_sensitive & option_bit);
      double alternate_best=1e100;int alternate_gap=n;
      for (int i=lo;i<=n;i++) {
          std::array<int,2> fc;
          for (int color=0;color<2;color++) {
              fc[color]=first[color]+(first[color]>=i);
              if (color==cx) fc[color]=std::min(fc[color],i);
          }
          double rank=adaptive_weights[x]*i+suffix[i];
          double value=adaptive_future*(adaptive_rank*rank/P+
              adaptive_holes[c][0]*fc[0]+adaptive_holes[c][1]*fc[1]);
          if (need && barrier<0) value+=fc[desired];
          // Recompute the alternative from the unpenalized value, rather than
          // subtracting the penalty: this preserves the original rounding.
          if (compare_modes) {
              double alternate=value;
              if (mode!=1 && i==0 && n) alternate+=adaptive_top_penalty;
              alternate+=1e-7*(n-i);
              if (alternate<alternate_best) {alternate_best=alternate;alternate_gap=i;}
          }
          if (mode==1 && i==0 && n) value+=adaptive_top_penalty;
          value+=1e-7*(n-i);
          if (value<best) {best=value;gap=i;}
      }
      if (compare_modes && alternate_gap!=gap) equivalence_sensitive|=option_bit;
      if (x==top_d) top_d=top_pred=-1;
      drop_filler(x);
      if (!n) {
          int anchor=-1;
          for (int k:order) {
              if (k==x || k==top_d || is_filler(k)) continue;
              if (block_of[k]>=0 || (col_of[k]>=0 && col_of[k]<c)) anchor=k;
          }
          if (anchor<0) move(x,0);else move_after(x,anchor);
      } else if (gap<n) {
          int from=index_of(x),to=index_of(v[gap]);
          move(x,from<to?to-1:to);
      } else move_after(x,v.back());
  }
  int index_of(int k) const {
      for (int i = 0; i < K; i++) if (order[i] == k) return i;
      return -1;
  }
  bool visible(int k) const {
      u64 e = paper[k].opaque;
      for (int x : order) {
          if (x == k) return e != 0;
          e &= ~paper[x].opaque;
          if (!e) return false;
      }
      return false;
  }
  u64 display() const {
      u64 covered = 0, black = 0;
      for (int k : order) {
          black |= paper[k].black & ~covered;
          covered |= paper[k].opaque;
          if (covered == ~u64(0)) break;
      }
      return black;
  }
  bool check_vis = false, invalid = false;
  void move(int k, int d) {
      int i = index_of(k);
      if (i == d) return;
      if (check_vis && !visible(k)) invalid = true;
      order.erase(order.begin() + i);
      order.insert(order.begin() + d, k);
      ops.push_back({k, d});
  }
  void move_after(int k, int x) {
      int i = index_of(k);
      if (index_of(x) + 1 == i) return;
      if (check_vis && !visible(k)) invalid = true;
      order.erase(order.begin() + i);
      int j = 0;
      while (order[j] != x) j++;
      order.insert(order.begin() + j + 1, k);
      ops.push_back({k, j + 1});
  }
  bool is_filler(int k) const {
      for (auto& f : fillers) if (f.paper == k) return true;
      return false;
  }
  void drop_filler(int k) {
      std::erase_if(fillers, [&](const Filler& f) { return f.paper == k; });
  }
  bool in_column(int k, int l) const { return col_of[k] == l && k != top_d && !is_filler(k); }
  void column_tops(int l, int n, std::vector<int>& top) const {
      top.clear();
      for (int k : order)
          if (in_column(k, l)) {
              top.push_back(k);
              if ((int)top.size() >= n) break;
          }
  }
  int column_top(int l) const {
      for (int k : order) if (in_column(k, l)) return k;
      return -1;
  }
  void dig(int l,int barrier=-1) {
      int t=column_top(l);
      if (t<0) {invalid=true;return;}
      if (barrier<0) {
          for (int k:order) if (in_column(k,l)) barrier=k;
      }
      if (t!=barrier) adaptive_insert(t,adaptive_request,barrier,2);
  }
  void lift(int d) {
      int c=col_of[d];
      for (int it=0;column_top(c)!=d;it++) {
          if (it>=K || invalid) {invalid=true;return;}
          dig(c,d);
      }
      move(d,0);
      top_d=d;
      top_pred=-1;
  }
  void set_handle(int l,int color) {
      int barrier=-1;
      for (int k:order) if (in_column(k,l) && int(paper[k].black >> handle[l] & 1)==color) {
          barrier=k;break;
      }
      if (barrier<0) {invalid=true;return;}
      for (int it=0;column_top(l)!=barrier;it++) {
          if (it>=K || invalid) {invalid=true;return;}
          dig(l,barrier);
      }
  }
  void fix_handles(int u, u64 hh) {
      for (int j = 0; j < H; j++)
          if (hh >> handle[j] & 1) set_handle(j, A[u] >> handle[j] & 1);
  }
  int handle_fix_cost(int l, int c) const {
      int i = 0;
      for (int k : order) {
          if (!in_column(k, l)) continue;
          if ((int)(paper[k].black >> handle[l] & 1) == c) return i;
          i++;
      }
      return 0;
  }
  std::vector<int> fix_costs(int u, u64 hh) const {
      std::vector<int> fix(H, 0);
      if (!hh) return fix;
      std::array<int,64> rank{};
      u64 remaining=hh;
      for (int k : order) {
          int c=col_of[k];
          if (c<0 || !(remaining >> handle[c] & 1) || !in_column(k,c)) continue;
          if (!((paper[k].black ^ A[u]) >> handle[c] & 1)) {
              fix[c]=rank[c];
              remaining&=~(u64(1)<<handle[c]);
              if (!remaining) break;
          } else rank[c]++;
      }
      return fix;
  }
  int level_past(u64 wrong) const {
      int lvl = 0;
      for (u64 x = wrong; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
      return lvl;
  }
  u64 shown_by(const Filler& f) const {
      u64 m = 0;
      for (int j = f.lvl; j <= f.hi; j++)
          if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
      return m;
  }
  static bool reaches_deeper(int lvl, int c, const std::vector<Filler>& placed) {
      for (auto& f : placed) if (f.lvl > lvl && c >= f.lvl) return true;
      return false;
  }
  void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
      int q = K, last_above = -1;
      for (int i = 0; i < K; i++) {
          int k = order[i];
          if (below_generic && k == base_paper) last_above = i;
          if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
          if (col_of[k] < lvl) last_above = i;
          else if (q == K) q = i;
      }
      int xi = index_of(x);
      if (lazy && xi < q && xi > last_above) return;
      move(x, xi < q ? q - 1 : q);
  }
  void place_filler(int c,int depth,int lvl,u64& hh) {
      std::vector<int> top;
      column_tops(c,depth+1,top);
      if (depth<0 || depth>=int(top.size())) {invalid=true;return;}
      int x=top[depth];
      for (int it=0;column_top(c)!=x;it++) {
          if (it>=K || invalid) {invalid=true;return;}
          dig(c,x);
      }
      move_to_level(x,lvl);
      fillers.push_back({x,-1,lvl,c});
      hh&=~shown_by(fillers.back());
  }
  void return_paper(int x,int u,int mode,unsigned option_bit=0) {
      adaptive_insert(x,u,-1,mode,option_bit);
  }

  struct PlanOpt {
      int ret_mode = 0;
      int fret_mode = 0;
      bool use_filler = false;
      bool keep = false;
      int fret_ret = 1;
  };
  struct FillerPick {
      int c = -1, depth = 0, lvl = 0;
      bool post = false;
  };
  struct Cand {
      int lvl;
      double gain;
      int c, depth;
      int kind = 0;
      int idx = -1;
      bool post = false;
  };
  std::vector<Cand> best_intervals(const std::vector<std::vector<Cand>>& cand) const {
      std::vector<double> best(H + 1, 0);
      std::vector<int> pick(H + 1, -1);
      for (int c = 0; c < H; c++) {
          best[c + 1] = best[c];
          for (int i = 0; i < (int)cand[c].size(); i++)
              if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9) {
                  best[c + 1] = best[cand[c][i].lvl] + cand[c][i].gain;
                  pick[c + 1] = i;
              }
      }
      std::vector<Cand> res;
      for (int j = H; j > 0;) {
          if (pick[j] < 0) {
              j--;
              continue;
          }
          res.push_back(cand[j - 1][pick[j]]);
          j = res.back().lvl;
      }
      return res;
  }
  static constexpr int kFillerDepth = 3, kFillerCost = 1, kMaxFillers = 8;
  struct ColumnHeads {
      std::array<std::array<int,kFillerDepth+1>,64> id{};
      std::array<int,64> count{};
  };
  ColumnHeads column_heads() const {
      ColumnHeads heads;
      for (int k : order) {
          int c=col_of[k];
          if (c<0 || heads.count[c]>kFillerDepth || !in_column(k,c)) continue;
          heads.id[c][heads.count[c]++]=k;
      }
      return heads;
  }
  std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {
      auto fix = fix_costs(u, hh);
      std::vector<std::vector<Cand>> cand(H);
      const auto heads=column_heads();
      for (int c = 0; c < H; c++) {
          if (!(hh >> handle[c] & 1)) continue;
          if (!heads.count[c] || heads.id[c][0] == d) continue;
          for (int depth = 0; depth < heads.count[c]; depth++) {
              u64 shown = paper[heads.id[c][depth]].opaque & hh;
              int lvl = level_past((paper[heads.id[c][depth]].black ^ A[u]) & shown);
              if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
              int save = 0;
              for (int j = lvl; j <= c; j++)
                  if ((j != c || depth) && (shown >> handle[j] & 1)) save += fix[j];
              int gain = save - kFillerCost - depth;
              if (gain > 0) cand[c].push_back({lvl, (double)gain, c, depth});
          }
      }
      std::vector<FillerPick> res;
      for (auto& cd : best_intervals(cand)) res.push_back({cd.c, cd.depth, cd.lvl, false});
      std::reverse(res.begin(), res.end());
      return res;
  }


  int level_for(int x, int d, u64 hh, int u, u64& cov) const {
      int cx = col_of[x], l = col_of[d];
      u64 shown = paper[x].opaque & hh;
      int lvl = level_past((paper[x].black ^ A[u]) & shown);
      if (cx >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
      cov = 0;
      for (int j = lvl; j <= cx; j++)
          if (shown >> handle[j] & 1) cov |= 1ULL << handle[j];
      return cov ? lvl : -1;
  }
  bool gen_harm(int x, int d, int u) const {
      if (d < 0 || index_of(x) > index_of(base_paper)) return false;
      return (paper[x].opaque & gmask & ~paper[d].opaque & (paper[x].black ^ A[u])) != 0;
  }
  void refill_or_return(int u, const std::vector<Filler>& olds, u64& pre_cov, std::vector<Filler>& placed,
                        int mode, bool keep_harmless) {
      int d = ded[u];
      for (int i = (int)olds.size() - 1; i >= 0; i--) {
          int x = olds[i].paper, cf = col_of[x];
          bool use = false;
          int lvl = 0;
          u64 cov = 0;
          if (d >= 0 && x != d && visible(x)) {
              lvl = level_for(x, d, hmask & ~paper[d].opaque & ~pre_cov, u, cov);
              if (lvl >= 0 && !reaches_deeper(lvl, cf, placed)) {
                  int save = 0;
                  for (int j = lvl; j <= cf; j++)
                      if (cov >> handle[j] & 1) save += handle_fix_cost(j, A[u] >> handle[j] & 1);
                  use = save >= 2;
              }
          }
          if (!use && keep_harmless && d >= 0 && x != d) {
              int L = olds[i].lvl, l = col_of[d];
              bool harm = (L <= l && l <= cf && (paper[x].opaque >> handle[l] & 1)) || reaches_deeper(L, cf, placed);
              u64 hcov = 0;
              for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
              hcov &= paper[x].opaque & hmask & ~paper[d].opaque & ~pre_cov;
              if ((paper[x].black ^ A[u]) & hcov || gen_harm(x, d, u)) harm = true;
              if (!harm && visible(x)) {
                  drop_filler(x);
                  placed.push_back(olds[i]);
                  pre_cov |= hcov;
                  continue;
              }
          }
          if (!use) {
              return_paper(x, u, mode, kFretRetSensitive);
              continue;
          }
          drop_filler(x);
          move_to_level(x, lvl, true, gen_harm(x, d, u));
          placed.push_back({x, olds[i].pred, lvl, cf});
          pre_cov |= cov;
      }
  }
  static constexpr double kRelevel = 0.5, kStay = 0.8;
  int depth_in_column(int x) const {
      int i = 0;
      for (int k : order) {
          if (k == x) return i;
          if (in_column(k, col_of[x])) i++;
      }
      return -1;
  }
  void run_joint(int u, const PlanOpt& opt) {
      int d = ded[u];
      if (d < 0 || d == top_d) {
          invalid = true;
          return;
      }
      const int l = col_of[d];
      const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
      u64 hh = hole_all & ~gmask;
      auto fix = fix_costs(u, hh);
      const bool d_out = is_filler(d);
      std::vector<Filler> olds;
      for (auto& f : fillers) if (f.paper != d) olds.push_back(f);
      const int x0 = top_d;
      std::vector<std::vector<Cand>> cand(H);
      auto mism_level = [&](int x) { return level_past((paper[x].black ^ A[u]) & paper[x].opaque & hh); };
      auto saved = [&](int x, int lvl, int c, bool skip_c) {
          int sv = 0;
          for (int j = lvl; j <= c; j++)
              if ((hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1) && !(skip_c && j == c)) sv += fix[j];
          return sv;
      };
      auto covers = [&](int x, int j) { return (hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1); };
      auto add_old = [&](int x, int idx, int L, bool is_x0) {
          int c = col_of[x];
          int lvl = mism_level(x);
          if (!is_x0 && gen_harm(x, d, u)) L = -2;
          if (!d_out && c >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
          if (lvl <= c) {
              int sv = saved(x, lvl, c, false);
              double g = sv - kRelevel;
              if (!is_x0 && lvl == L) g = sv + 1 - kStay;
              if (g > 0) cand[c].push_back({lvl, g, c, 0, is_x0 ? 3 : (lvl == L ? 2 : 1), idx});
          }
          if (!is_x0 && L > lvl && L <= c) {
              bool harm = !d_out && L <= l && l <= c && (paper[x].opaque >> handle[l] & 1);
              double g = saved(x, L, c, false) + 1 - kStay;
              if (!harm && g > 0) cand[c].push_back({L, g, c, 0, 2, idx});
          }
          for (int lv = lvl + 1; lv <= c; lv++) {
              if (!covers(x, lv) || (!is_x0 && lv == L)) continue;
              double g = saved(x, lv, c, false) - kRelevel;
              if (g > 0) cand[c].push_back({lv, g, c, 0, is_x0 ? 3 : 1, idx});
          }
      };
      for (int i = 0; i < (int)olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
      if (x0 >= 0) add_old(x0, -1, -1, true);
      const auto heads=column_heads();
      for (int c = 0; c < H; c++) {
          bool hole_c = hh >> handle[c] & 1;
          if (c == l || (d_out && !hole_c)) continue;
          for (int depth = 0; depth < heads.count[c]; depth++) {
              int f = heads.id[c][depth];
              int lvl = mism_level(f);
              for (int lv = lvl; lv <= c; lv++) {
                  if (lv > lvl && !covers(f, lv)) continue;
                  bool post = d_out || (c > l && lv <= l && (paper[f].opaque >> handle[l] & 1));
                  int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                  if (g >= kFillerCost) cand[c].push_back({lv, (double)g, c, 0, 0, f, post});
              }
          }
      }
      const auto picks = best_intervals(cand);
      std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);
      int x0_lvl = -1;
      for (auto& cd : picks) {
          if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
          if (cd.kind == 3) x0_lvl = cd.lvl;
      }
      Filler fd{d, -1};
      for (auto& f : fillers) if (f.paper == d) fd = f;
      fillers = olds;
      if (d_out) fillers.push_back(fd);
      std::vector<char> done(olds.size(), 0);
      for (int i = (int)olds.size() - 1; i >= 0; i--) {
          if (old_dec[i] != 0 || !visible(olds[i].paper)) continue;
          return_paper(olds[i].paper, u, opt.fret_ret, kFretRetSensitive);
          done[i] = 1;
      }
      if (x0 >= 0) {
          if (x0_lvl >= 0) {
              top_d = -1;
              move_to_level(x0, x0_lvl, true, gen_harm(x0, d, u));
              fillers.push_back({x0, top_pred, x0_lvl, col_of[x0]});
              top_pred = -1;
          } else {
              return_paper(x0, u, opt.ret_mode, kRetSensitive);
          }
      }
      for (int i = (int)olds.size() - 1; i >= 0; i--)
          if (old_dec[i] == 0 && !done[i]) return_paper(olds[i].paper, u, opt.fret_ret, kFretRetSensitive);
      for (int i = 0; i < (int)olds.size(); i++) {
          if (old_dec[i] == 0) continue;
          int x = olds[i].paper;
          for (auto& f : fillers)
              if (f.paper == x) f.lvl = old_lvl[i], f.hi = col_of[x];
          if (old_dec[i] == 1) move_to_level(x, old_lvl[i], true, gen_harm(x, d, u));
      }
      for (auto& f : fillers) if (f.paper != d) hh &= ~shown_by(f);
      set_blocks(wanted_blocks(u, hole_all));
      for (auto& cd : picks)
          if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
      if (d_out) {
          drop_filler(d);
          move(d, 0);
          top_d = d;
          top_pred = fd.pred;
      } else {
          lift(d);
      }
      for (auto& cd : picks)
          if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
      fix_handles(u, hh);
  }
  void run_plan(int u, const PlanOpt& opt) {
      if (opt.fret_mode == 5) {
          run_joint(u, opt);
          return;
      }
      const bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
      u64 pre_cov = 0;
      int stay = -1, stay_pred = -1;
      if (opt.ret_mode == 4) {
          int d = ded[u];
          if (top_d < 0 || kept || d < 0 || d == top_d || (gmask & ~paper[d].opaque & paper[top_d].opaque)) {
              invalid = true;
              return;
          }
          stay = top_d, stay_pred = top_pred;
          top_d = top_pred = -1;
      }
      if (top_d >= 0 && !kept && opt.ret_mode == 3) {
          int x = top_d, lp = col_of[x], d = ded[u];
          if (d < 0 || d == x) {
              invalid = true;
              return;
          }
          u64 cov0 = 0;
          int lvl = level_for(x, d, hmask & ~paper[d].opaque, u, cov0);
          if (lvl < 0) {
              invalid = true;
              return;
          }
          std::vector<Filler> vis_old, def_old;
          for (auto& f : fillers) (visible(f.paper) ? vis_old : def_old).push_back(f);
          std::vector<Filler> placed = {{x, top_pred, lvl, lp}};
          pre_cov |= cov0;
          auto put_back = [&](const std::vector<Filler>& olds) {
              if (opt.fret_mode >= 3) refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
              else for (int i = (int)olds.size() - 1; i >= 0; i--) return_paper(olds[i].paper, u, opt.fret_mode, kFretSensitive);
          };
          put_back(vis_old);
          move_to_level(x, lvl);
          top_d = top_pred = -1;
          put_back(def_old);
          for (auto& f : placed) fillers.push_back(f);
      } else {
          if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode, kRetSensitive);
          if (opt.fret_mode >= 3) {
              std::vector<Filler> olds = fillers, placed;
              refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
              for (auto& f : placed) fillers.push_back(f);
          } else {
              while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode, kFretSensitive);
          }
      }
      if (stay >= 0) {
          fillers.push_back({stay, stay_pred, 0, col_of[stay]});
          pre_cov |= shown_by(fillers.back());
      }
      if (ded[u] < 0) {
          set_blocks(wanted_blocks(u, gmask));
          for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
          return;
      }
      const int d = ded[u];
      const u64 holes = (gmask | hmask) & ~paper[d].opaque;
      set_blocks(wanted_blocks(u, holes));
      u64 hh = holes & ~gmask & ~pre_cov;
      if (!kept && opt.use_filler) {
          auto picks = choose_fillers_prelift(u, d, hh);
          for (auto& pk : picks) if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
          lift(d);
          for (auto& pk : picks) if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
      } else {
          if (!kept) lift(d);
          if (opt.use_filler)
              for (auto& pk : choose_fillers_dp(u, d, hh)) {
                  if ((int)fillers.size() >= kMaxFillers) break;
                  place_filler(pk.c, pk.depth, pk.lvl, hh);
              }
      }
      fix_handles(u, hh);
  }
  std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) const {
      const int l = col_of[d];
      const u64 hole_all = hmask & ~paper[d].opaque;
      u64 covered = 0;
      for (auto& f : fillers) covered |= shown_by(f);
      auto fix = fix_costs(u, hh);
      std::vector<std::vector<Cand>> cand(H);
      const auto heads=column_heads();
      for (int c = 0; c < H; c++) {
          if (c == l || (covered >> handle[c] & 1)) continue;
          bool hole_c = hole_all >> handle[c] & 1;
          for (int depth = 0; depth < heads.count[c]; depth++) {
              int f = heads.id[c][depth];
              u64 shown = paper[f].opaque & hh;
              int lvl = level_past((paper[f].black ^ A[u]) & shown);
              if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
              for (int lv = lvl; lv <= c; lv++) {
                  if (lv > lvl && (!(shown >> handle[lv] & 1) || reaches_deeper(lv, c, fillers))) continue;
                  bool post = c > l && lv <= l && (paper[f].opaque >> handle[l] & 1);
                  int save = 0;
                  for (int j = lv; j <= c; j++)
                      if ((shown >> handle[j] & 1) && (j != c || depth || !hole_c)) save += fix[j];
                  int gain = save - kFillerCost - depth;
                  if (gain > 0) cand[c].push_back({lv, (double)gain, c, depth, 0, -1, post});
              }
          }
      }
      struct PC {
          int c, depth;
          u64 opq, shown, bad;
          bool hole_c;
          int fsum;
      };
      struct Stack {
          int cU, dU, cL, dL;
          bool postU, postL;
      };
      std::vector<Stack> stacks;
      auto hib = [](u64 x) { return x ? 63 - __builtin_clzll(x) : -1; };
      auto upto = [](int b) -> u64 { return b < 0 ? 0 : b >= 63 ? ~0ULL : (1ULL << (b + 1)) - 1; };
      const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
      std::vector<PC> pcs;
      std::vector<int> first_of(H + 1, 0);
      for (int c = 0; c < H; c++) {
          first_of[c] = pcs.size();
          if (c == l || (covered >> handle[c] & 1)) continue;
          for (int dpt = 0; dpt < heads.count[c]; dpt++) {
              int k = heads.id[c][dpt];
              PC pc{c, dpt, h_opq[k] & upto(c), 0, 0, (bool)(hole_all >> handle[c] & 1), 0};
              pc.shown = pc.opq & hh_i;
              pc.bad = pc.shown & (h_blk[k] ^ au_i);
              for (u64 x = pc.shown; x; x &= x - 1) pc.fsum += fix[__builtin_ctzll(x)];
              pcs.push_back(pc);
          }
      }
      first_of[H] = pcs.size();
      for (auto& L : pcs) {
          if (!L.bad) continue;
          for (int ui = first_of[std::max(hib(L.bad), 0)]; ui < first_of[L.c]; ui++) {
              const PC& U = pcs[ui];
              if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 2) continue;
              int aU = hib(U.bad) + 1;
              if (aU > U.c) continue;
              int a = std::max(aU, hib(L.bad & ~U.opq & upto(U.c)) + 1);
              if (a > U.c) continue;
              bool postU = U.c > l && a <= l && (U.opq >> l & 1);
              bool postL = postU || (L.c > l && a <= l && (L.opq >> l & 1));
              if ((postU && !U.hole_c) || (postL && !L.hole_c) || reaches_deeper(a, L.c, fillers)) continue;
              u64 from_a = ~upto(a - 1);
              u64 covU = U.shown & from_a & upto(U.c), covL = L.shown & ~U.opq & from_a & upto(L.c);
              if (U.depth == 0 && U.hole_c) covU &= ~(1ULL << U.c);
              if (L.depth == 0 && L.hole_c) covL &= ~(1ULL << L.c);
              int save = 0;
              for (u64 x = covU | covL; x; x &= x - 1) save += fix[__builtin_ctzll(x)];
              int gain = save - 2 * kFillerCost - U.depth - L.depth;
              if (gain < 2) continue;
              stacks.push_back({U.c, U.depth, L.c, L.depth, postU, postL});
              cand[L.c].push_back({a, (double)gain, L.c, -(int)stacks.size()});
          }
      }
      std::vector<FillerPick> res;
      for (auto& cd : best_intervals(cand)) {
          if (cd.depth < 0) {
              const Stack& st = stacks[-1 - cd.depth];
              res.push_back({st.cL, st.dL, cd.lvl, st.postL});
              res.push_back({st.cU, st.dU, cd.lvl, st.postU});
          } else {
              res.push_back({cd.c, cd.depth, cd.lvl, cd.post});
          }
      }
      std::reverse(res.begin(), res.end());
      return res;
  }

  bool fillers_reachable() const {
      if (fillers.empty()) return true;
      std::array<unsigned char,K> needed{};
      int remaining=0;
      for (const auto& f : fillers) if (!needed[f.paper]) {
          needed[f.paper]=1;
          remaining++;
      }
      u64 covered=0;
      for (int x : order) {
          if (x==top_d) continue;
          if (needed[x]) {
              if (!(paper[x].opaque & ~covered)) return false;
              if (--remaining==0) return true;
          }
          covered|=paper[x].opaque;
          if (covered==~u64(0)) return false;
      }
      return false;
  }
  double tops_penalty() const {
      static std::vector<char> seen;
      seen.assign(H, 0);
      double pen = 0;
      int found = 0;
      for (int k : order) {
          int l = col_of[k];
          if (l < 0 || seen[l] || !in_column(k, l)) continue;
          seen[l] = 1;
          if ((int)(paper[k].black >> handle[l] & 1) != bias_c[l]) pen += bias_g[l];
          if (++found == H) break;
      }
      return pen;
  }
  void merge_double_moves(const std::vector<int>& start, std::vector<std::pair<int, int>>& mvs) const {
      bool dup = false;
      for (size_t i = 0; i < mvs.size() && !dup; i++)
          for (size_t j = i + 1; j < mvs.size() && !dup; j++) dup = mvs[i].first == mvs[j].first;
      if (!dup) return;
      struct M {
          int k, anchor, pos;
      };
      auto apply = [](std::vector<int>& ord, const M& m) {
          ord.erase(std::find(ord.begin(), ord.end(), m.k));
          if (m.anchor == -2) ord.insert(ord.begin() + m.pos, m.k);
          else if (m.anchor < 0) ord.insert(ord.begin(), m.k);
          else ord.insert(std::find(ord.begin(), ord.end(), m.anchor) + 1, m.k);
      };
      auto vis = [&](const std::vector<int>& ord, int k) {
          u64 cov = 0;
          for (int x : ord) {
              if (x == k) return (paper[k].opaque & ~cov) != 0;
              cov |= paper[x].opaque;
          }
          return false;
      };
      std::vector<int> want = start;
      std::vector<M> mv;
      for (auto [k, d] : mvs) {
          want.erase(std::find(want.begin(), want.end(), k));
          mv.push_back({k, d == 0 ? -1 : want[d - 1], 0});
          want.insert(want.begin() + d, k);
      }
      auto replay_ok = [&](const std::vector<M>& ms, int skip) {
          std::vector<int> ord = start;
          for (int t = 0; t < (int)ms.size(); t++) {
              if (t == skip) continue;
              if (ms[t].anchor == ms[t].k || !vis(ord, ms[t].k)) return false;
              apply(ord, ms[t]);
          }
          return ord == want;
      };
      for (bool again = true; again;) {
          again = false;
          for (int i = 0; i < (int)mv.size() && !again; i++)
              for (int j = i + 1; j < (int)mv.size(); j++) {
                  if (mv[j].k != mv[i].k) continue;
                  int k = mv[i].k;
                  std::vector<int> st = start;
                  for (int t = 0; t < i; t++) apply(st, mv[t]);
                  std::vector<int> s2 = st;
                  for (int t = i; t <= j; t++) apply(s2, mv[t]);
                  int pj = std::find(s2.begin(), s2.end(), k) - s2.begin();
                  st.erase(std::find(st.begin(), st.end(), k));
                  int pa = mv[j].anchor < 0 ? 0 : (int)(std::find(st.begin(), st.end(), mv[j].anchor) - st.begin()) + 1;
                  for (int p : {pj, pa}) {
                      if (p > (int)st.size()) continue;
                      auto m2 = mv;
                      m2[i] = {k, -2, p};
                      if (replay_ok(m2, j)) {
                          m2.erase(m2.begin() + j);
                          mv = m2;
                          again = true;
                          break;
                      }
                  }
                  if (!again && replay_ok(mv, i)) {
                      mv.erase(mv.begin() + i);
                      again = true;
                  }
                  break;
              }
      }
      std::vector<int> ord = start;
      mvs.clear();
      for (auto& m : mv) {
          int before = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
          apply(ord, m);
          int after = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
          if (after != before) mvs.push_back({m.k, after});
      }
  }

  std::vector<std::vector<int>> cyc;
  std::vector<int> cpos;
  void init_cycles() {
      cyc.assign(H, {});
      cpos.assign(K, -1);
      for (int k : order)
          if (col_of[k] >= 0) {
              cpos[k] = cyc[col_of[k]].size();
              cyc[col_of[k]].push_back(k);
          }
  }
  void canonicalize() {
      std::vector<char> inpl(K,0);
      std::vector<int> lv(K,-1);
      int cur=H;
      bool gen_seen=false;
      for (int i=K-1;i>=0;i--) {
          int k=order[i],c=col_of[k];
          if (c<0) {if (block_of[k]>=0) gen_seen=true;continue;}
          if (!gen_seen && c<=cur) {cur=c;inpl[k]=1;}
          else lv[k]=gen_seen?0:std::min(cur,c);
      }
      int ntop=-1;
      std::vector<Filler> nf;
      for (int i=0;i<K;i++) {
          int k=order[i];
          if (col_of[k]<0 || inpl[k]) continue;
          if (i==0) ntop=k;
          else nf.push_back({k,-1,lv[k],col_of[k]});
      }
      std::vector<Filler> res;
      for (auto& f:fillers) for (auto& g:nf) if (g.paper==f.paper) res.push_back(g);
      for (auto& g:nf) if (!is_filler(g.paper)) res.push_back(g);
      top_d=ntop;top_pred=-1;fillers=res;
  }
  struct State {
      std::vector<int> order;
      int top_d, top_pred;
      std::vector<Filler> fillers;
  };
  State save() const { return {order, top_d, top_pred, fillers}; }
  void restore(const State& st) {
      order = st.order;
      top_d = st.top_d;
      top_pred = st.top_pred;
      fillers = st.fillers;
  }
  static constexpr double kFillerCharge = 0.8, kTopValue = 0.55;
#ifdef BARCODE_DISABLE_POST
  static constexpr int postMode = 0;
#elif defined(BARCODE_POST_MODE)
  static constexpr int postMode = BARCODE_POST_MODE;
#else
  static constexpr int postMode = 5;
#endif
  long long postSaved = 0, postChanged = 0, postCandidates = 0;
  long long ejectTrials = 0, ejectCandidates = 0, ejectChanged = 0, ejectSaved = 0;
  long long postSplitStates = 0, postRecoveries = 0;
#ifndef BARCODE_EJECT_TRIALS
#define BARCODE_EJECT_TRIALS 64
#endif
#ifndef BARCODE_EJECT_GAPS
#define BARCODE_EJECT_GAPS 6
#endif
#ifndef BARCODE_EJECT_EVALS
#define BARCODE_EJECT_EVALS 24
#endif

  // A response is specified by its visible barcode, rather than by one exact
  // final permutation. Preserve paper anchors while editing the move list.
  // Modes: 1 single deletion; 2 adds all moved-paper anchors; 3 restricts
  // anchors to old main/fillers/repeated papers; 4 adds pair deletion;
  // 5 combines pair deletion with the restricted anchor search.
  std::vector<std::pair<int,int>> post_optimize(
      const State& initial, std::vector<std::pair<int,int>> input_ops, int u) {
      if (postMode == 0 || input_ops.empty()) return input_ops;
      struct Edit { int paper, anchor; };
      auto anchorize = [&](const std::vector<std::pair<int,int>>& path) {
          std::vector<int> ord = initial.order;
          std::vector<Edit> edits;
          edits.reserve(path.size());
          for (auto [k,d] : path) {
              auto it = std::find(ord.begin(),ord.end(),k);
              ord.erase(it);
              edits.push_back({k,d ? ord[d-1] : -1});
              ord.insert(ord.begin()+d,k);
          }
          return edits;
      };
      auto edits = anchorize(input_ops);
      std::array<bool,K> initial_extra{};
      if (initial.top_d >= 0) initial_extra[initial.top_d] = true;
      for (const auto& f : initial.fillers) initial_extra[f.paper] = true;

      // Every candidate must rebuild its bookkeeping from the same saved
      // filler list. canonicalize() retains that list's relative priority
      // and adds new outliers; previous trial state must never leak into it.
      const State bookkeeping_seed = save();
      State best_state = bookkeeping_seed;
      auto best_ops = input_ops;
      auto score = [&](size_t count) {
          double future = adaptive_end_weight > 0
              ? adaptive_end_weight * adaptive_next_cost()
              : kTopValue * tops_penalty();
          return count + kFillerCharge * fillers.size() + future;
      };
      double best_score = score(best_ops.size());
      auto evaluate = [&](const std::vector<Edit>& trial) {
          ++postCandidates;
          std::vector<int> ord = initial.order;
          std::vector<std::pair<int,int>> path;
          path.reserve(trial.size());
          for (auto [k,a] : trial) {
              if (k < 0 || k >= K || a == k || a < -1 || a >= K) return false;
              int p = int(std::find(ord.begin(),ord.end(),k)-ord.begin());
              if (p >= K) return false;
              int dest = 0;
              if (a >= 0) {
                  auto it = std::find(ord.begin(),ord.end(),a);
                  if (it == ord.end()) return false;
                  dest = int(it-ord.begin())+1;
              }
              if (p < dest) --dest;
              // No-op edits are omitted, so they require no visibility.
              if (p == dest) continue;
              u64 covered = 0;
              for (int i=0;i<p;i++) covered |= paper[ord[i]].opaque;
              if (!(paper[k].opaque & ~covered)) return false;
              ord.erase(ord.begin()+p);
              ord.insert(ord.begin()+dest,k);
              path.push_back({k,dest});
          }
          if (path.size() > 2*K) return false;
          u64 covered = 0, shown = 0;
          int first_generic = -1, last_generic = -1, generic_count = 0;
          for (int i=0;i<K;i++) {
              int k = ord[i];
              shown |= paper[k].black & ~covered;
              covered |= paper[k].opaque;
              if (block_of[k] >= 0) {
                  if (first_generic < 0) first_generic = i;
                  last_generic = i;
                  ++generic_count;
              }
          }
          if (shown != A[u] || generic_count != M ||
              (!BARCODE_RELAX_GENERIC && last_generic-first_generic+1 != M)) return false;
          restore(bookkeeping_seed);
          order = std::move(ord);
          canonicalize();
          // The default/fast plan returns old fillers before reconfiguring
          // the generic block. Retain its reachability precondition.
          if (!fillers_reachable()) return false;
          double value = score(path.size());
          if (value+1e-8 >= best_score) return false;
          best_score = value;
          best_ops = std::move(path);
          best_state = save();
          return true;
      };

      bool changed = false;
      auto delete_singles = [&]() {
          bool any = false;
          for (int i=int(edits.size())-1;i>=0;i--) {
              auto trial = edits;
              trial.erase(trial.begin()+i);
              if (evaluate(trial)) {
                  edits = anchorize(best_ops);
                  any = changed = true;
                  // Other edits may have become no-ops and disappeared.
                  i = std::min(i,int(edits.size()));
              }
          }
          return any;
      };
      for (int pass=0;pass<3;pass++) if (!delete_singles()) break;
      if (postMode == 4 || postMode == 5) {
          for (int round=0;round<4;round++) {
              bool improved = false;
              for (int j=int(edits.size())-1;j>=1 && !improved;j--)
                  for (int i=j-1;i>=0 && !improved;i--) {
                      auto trial = edits;
                      trial.erase(trial.begin()+j);
                      trial.erase(trial.begin()+i);
                      if (evaluate(trial)) {
                          edits = anchorize(best_ops);
                          changed = improved = true;
                      }
                  }
              if (!improved) break;
              delete_singles();
          }
      }
      if (postMode == 2 || postMode == 3 || postMode == 5) {
          for (int i=int(edits.size())-1;i>=0;i--) {
              int k = edits[i].paper;
              if (postMode >= 3 && !initial_extra[k]) {
                  int repeats = 0;
                  for (const auto& e : edits) repeats += e.paper == k;
                  if (repeats < 2) continue;
              }
              auto ord = initial.order;
              for (int t=0;t<i;t++) {
                  auto [x,a] = edits[t];
                  ord.erase(std::find(ord.begin(),ord.end(),x));
                  int d = a < 0 ? 0
                      : int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;
                  ord.insert(ord.begin()+d,x);
              }
              std::vector<int> anchors{-1};
              auto add = [&](int a) {
                  if (a != k && std::find(anchors.begin(),anchors.end(),a) == anchors.end())
                      anchors.push_back(a);
              };
              int last = -1;
              std::array<bool,64> seen{};
              for (int x : ord) if (x != k) {
                  if (col_of[k] < 0) {
                      if (col_of[x] < 0) { add(last); add(x); }
                  } else {
                      if (col_of[x] >= 0 && !seen[col_of[x]]) {
                          seen[col_of[x]] = true;
                          if (col_of[x] <= col_of[k]) add(last);
                      }
                      if (col_of[x] == col_of[k]) { add(last); add(x); }
                      if (col_of[x] < 0) add(x);
                  }
                  last = x;
              }
              for (int t=i+1;t<int(edits.size());t++)
                  if (edits[t].paper == k) add(edits[t].anchor);
              auto chosen = edits;
              for (int a : anchors) {
                  if (a == edits[i].anchor) continue;
                  auto trial = edits;
                  trial[i].anchor = a;
                  if (evaluate(trial)) {
                      chosen = anchorize(best_ops);
                      changed = true;
                  }
              }
              edits = std::move(chosen);
              i = std::min(i,int(edits.size()));
          }
          delete_singles();
      }
#ifndef BARCODE_DISABLE_EJECT
      // Delete two existing moves, then repair the resulting barcode by
      // moving one currently visible paper. This permits a different paper
      // to replace the combined effect of the removed moves.
      if (edits.size() >= 2) {
          const auto base_edits = edits;
          const int before_count = int(best_ops.size());
          int trials_left = BARCODE_EJECT_TRIALS;
          int evals_left = BARCODE_EJECT_EVALS;
          bool eject_improved = false;
          auto replay = [&](const std::vector<Edit>& trial, std::vector<int>& ord) {
              ord = initial.order;
              for (auto [k,a] : trial) {
                  int p = int(std::find(ord.begin(),ord.end(),k)-ord.begin());
                  if (p >= K || a == k) return false;
                  int d = a < 0 ? 0
                      : int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;
                  if (p < d) --d;
                  if (p == d) continue;
                  u64 covered = 0;
                  for (int t=0;t<p;t++) covered |= paper[ord[t]].opaque;
                  if (!(paper[k].opaque & ~covered)) return false;
                  ord.erase(ord.begin()+p);
                  ord.insert(ord.begin()+d,k);
              }
              return true;
          };
          for (int j=int(base_edits.size())-1;j>=1 && trials_left>0 && evals_left>0;j--)
              for (int i=j-1;i>=0 && trials_left>0 && evals_left>0;i--) {
                  --trials_left;
                  ++ejectTrials;
                  auto trial = base_edits;
                  trial.erase(trial.begin()+j);
                  trial.erase(trial.begin()+i);
                  std::vector<int> ord;
                  if (!replay(trial,ord)) continue;

                  // The owner and runner-up of every window determine the
                  // complete display after removing any visible paper.
                  std::array<int,64> first, second;
                  first.fill(K); second.fill(K);
                  std::array<u64,K> owned{};
                  std::vector<int> visible_papers;
                  u64 covered = 0, twice = 0, shown = 0, second_black = 0;
                  for (int t=0;t<K;t++) {
                      int k = ord[t];
                      u64 second_here = paper[k].opaque & covered & ~twice;
                      second_black |= paper[k].black & second_here;
                      for (u64 bits=second_here;bits;bits&=bits-1)
                          second[__builtin_ctzll(bits)] = t;
                      twice |= second_here;
                      u64 first_here = paper[k].opaque & ~covered;
                      if (first_here) {
                          visible_papers.push_back(k);
                          owned[k] = first_here;
                          for (u64 bits=first_here;bits;bits&=bits-1)
                              first[__builtin_ctzll(bits)] = t;
                          shown |= paper[k].black & first_here;
                      }
                      covered |= paper[k].opaque;
                      if (twice == ~u64(0)) break;
                  }
                  // Focus this neighborhood on simultaneous repairs.
                  if (__builtin_popcountll(shown ^ A[u]) < 2) continue;
                  for (int k : visible_papers) {
                      if (evals_left <= 0) break;
                      u64 after_removal = shown ^ ((shown ^ second_black) & owned[k]);
                      u64 bad = after_removal ^ A[u];
                      u64 wrong_color = paper[k].opaque & (paper[k].black ^ A[u]);
                      if ((bad & ~paper[k].opaque) || (bad & wrong_color)) continue;
                      int pos_k = int(std::find(ord.begin(),ord.end(),k)-ord.begin());
                      auto without_pos = [&](int window) {
                          int p = first[window] == pos_k ? second[window] : first[window];
                          // K also serves as the default-white sentinel;
                          // after removal it becomes K-1, below every sheet.
                          return p-int(p>pos_k);
                      };
                      int lo = 0, hi = K-1;
                      for (u64 bits=bad;bits;bits&=bits-1)
                          hi = std::min(hi,without_pos(__builtin_ctzll(bits)));
                      for (u64 bits=wrong_color;bits && lo<=hi;bits&=bits-1)
                          lo = std::max(lo,without_pos(__builtin_ctzll(bits))+1);
                      if (lo > hi) continue;
                      std::vector<int> without = ord;
                      without.erase(without.begin()+pos_k);
                      std::vector<int> gaps;
                      auto add_gap = [&](int d) {
                          if (d >= lo && d <= hi && d != pos_k &&
                              std::find(gaps.begin(),gaps.end(),d) == gaps.end())
                              gaps.push_back(d);
                      };
                      add_gap(lo); add_gap(hi);
                      // Same-column positions can avoid leaving a new
                      // filler. Other candidates use structural boundaries.
                      for (int t=0;t<K-1;t++) if (col_of[without[t]] == col_of[k]) {
                          add_gap(t); add_gap(t+1);
                      }
                      std::array<bool,64> seen{};
                      for (int t=0;t<K-1;t++) {
                          int c = col_of[without[t]];
                          if (c < 0) { add_gap(t); add_gap(t+1); }
                          else if (!seen[c]) {
                              seen[c] = true;
                              if (c <= col_of[k]) add_gap(t);
                          }
                      }
                      int limit = std::min(int(gaps.size()),int(BARCODE_EJECT_GAPS));
                      for (int z=0;z<limit && evals_left>0;z++) {
                          int d = gaps[z];
                          int anchor = d ? without[d-1] : -1;
                          trial.push_back({k,anchor});
                          --evals_left;
                          ++ejectCandidates;
                          if (evaluate(trial)) eject_improved = changed = true;
                          trial.pop_back();
                      }
                  }
              }
          if (eject_improved) {
              ++ejectChanged;
              ejectSaved += before_count-int(best_ops.size());
              edits = anchorize(best_ops);
          }
      }
#endif
      if (changed) ++postChanged;
      postSaved += int(input_ops.size())-int(best_ops.size());
      restore(best_state);
      if(BARCODE_RELAX_GENERIC){
          int a=-1,b=-1;
          for(int i=0;i<K;i++)if(block_of[order[i]]>=0){if(a<0)a=i;b=i;}
          postSplitStates+=b-a+1!=M;
      }
      return best_ops;
  }

  std::vector<std::pair<int, int>> process(int u) {
      init_adaptive();adaptive_request=u;
      if (fast_mode) {
          fast_requests++;
          ops.clear();invalid=false;check_vis=true;
          run_plan(u,PlanOpt{});
          check_vis=false;
          canonicalize();
          return ops;
      }
      const State st0 = save();
      const int top0 = top_d, d = ded[u];
      bool free_filler = false;
      for (auto& f : fillers) free_filler |= f.pred < 0;
      const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
      const std::vector<int> frets = free_filler ? std::vector<int>{1, 0} : std::vector<int>{1};
      auto skip = [&](int fm) { return (fm == 2 && !free_filler) || (fm >= 3 && fillers.empty()); };
      std::vector<PlanOpt> opts;
      for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
          for (int fm : {1, 2, 3, 4})
              for (int kp = 0; kp < ((top0 >= 0 && d == top0) ? 2 : 1); kp++)
                  for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                      if (!skip(fm)) opts.push_back({rm, fm, true, kp == 1, fr});
      if (d >= 0 && d != top0)
          for (int rm = 1; rm <= 2; rm++)
              for (int fr : frets) opts.push_back({rm, 5, true, false, fr});
      if (prev_ok)
          for (int fm : {1, 2, 3, 4})
              for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                  if (!skip(fm)) opts.push_back({4, fm, true, false, fr});
      double best = 1e18;
      std::vector<std::pair<int, int>> best_ops;
      State best_state;
      struct EquivalentPlan { PlanOpt opt; unsigned sensitive; };
      std::vector<EquivalentPlan> evaluated;
      evaluated.reserve(opts.size());
      auto equivalent=[](const EquivalentPlan& e,const PlanOpt& o) {
          const auto& p=e.opt;
          if (p.keep!=o.keep || p.use_filler!=o.use_filler) return false;
          if (p.ret_mode!=o.ret_mode &&
              (!(p.ret_mode>=1 && p.ret_mode<=2 && o.ret_mode>=1 && o.ret_mode<=2) ||
               (e.sensitive & kRetSensitive))) return false;
          if (p.fret_mode!=o.fret_mode &&
              (!(p.fret_mode>=1 && p.fret_mode<=2 && o.fret_mode>=1 && o.fret_mode<=2) ||
               (e.sensitive & kFretSensitive))) return false;
          if (p.fret_ret!=o.fret_ret && (e.sensitive & kFretRetSensitive)) return false;
          return true;
      };
      check_vis = true;
      for (const PlanOpt& o : opts) {
          bool duplicate=false;
          for (const auto& e : evaluated) if (equivalent(e,o)) { duplicate=true; break; }
          if (duplicate) { duplicate_candidates++; continue; }
          restore(st0);
          ops.clear();
          invalid = false;
          check_equivalence=true;
          equivalence_sensitive=0;
          run_plan(u, o);
          check_equivalence=false;
          evaluated.push_back({o,equivalence_sensitive});
          evaluated_candidates++;
          if (invalid || ops.size()>2*K || display() != A[u] || !fillers_reachable()) continue;
          merge_double_moves(st0.order, ops);
          double future = adaptive_end_weight>0 ? adaptive_end_weight*adaptive_next_cost() : kTopValue*tops_penalty();
          double cost = ops.size() + kFillerCharge * fillers.size() + future;
          if (cost < best) best = cost, best_ops = ops, best_state = save();
      }
      check_vis = false;
      if (best > 1e17) {
          adaptive_failures++;
          restore(st0);
          ops.clear();
          invalid = false;
          run_plan(u, PlanOpt{});
          return ops;
      }
      restore(best_state);
      canonicalize();
      if(BARCODE_RELAX_GENERIC && !fillers_reachable()){
          ++postRecoveries;
          restore(st0);ops.clear();invalid=false;check_vis=true;
          run_plan(u,PlanOpt{});check_vis=false;canonicalize();
          return ops;
      }
      return post_optimize(st0, std::move(best_ops), u);
  }

};
}

using U64=uint64_t;

// Guaranteed emergency design: one white and one black single-window sheet
// per window. Moving the visible member of a pair to the bottom toggles it.
int independent_bits(const std::vector<U64>& A,int R) {
    std::string output;
    for(int k=0;k<192;k++) {
        std::string row(64,'.');
        if(k<128)row[k%64]=k<64?'0':'1';
        output+=row+'\n';
    }
    std::cout<<output<<std::flush;
    U64 current=0;
    long long total=0;
    for(int r=0;r<R;r++) {
        int u;if(!(std::cin>>u)||u==-1)return 0;
        U64 different=current^A[u];
        output=std::to_string(__builtin_popcountll(different))+'\n';
        for(U64 s=different;s;s&=s-1) {
            int j=__builtin_ctzll(s),paper=j+((current>>j&1)?64:0);
            output+=std::to_string(paper)+" 191\n";
            total++;
        }
        current=A[u];
        std::cout<<output<<std::flush;
    }
    std::cerr<<"moves = "<<total<<"\nemergency_design = 1\n";
    return 0;
}

int main(){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    const auto start=std::chrono::steady_clock::now();
    auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    int N,K,P,R;if(!(std::cin>>N>>K>>P>>R))return 0;
    std::vector<U64>A(P);
    for(auto& a:A){std::string s;std::cin>>s;a=0;for(int j=0;j<N;j++)if(s[j]=='1')a|=U64(1)<<j;}
    if(N!=64||K!=192||P!=256)return 0;
    const auto originalA=A;
#ifdef BARCODE_FORCE_FALLBACK
    return independent_bits(originalA,R);
#endif
    std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
    int M=6,G=36;
    Comparator comp;
    std::mt19937_64 rng(779879);
    std::unique_ptr<PaperDesign> des;
    int mappingIterations=0;
    for(int attempt=0;;attempt++){
        A=originalA;std::iota(permutation.begin(),permutation.end(),0);
        comp.init(M,G,rng);
        if(attempt<2) {
            const double cap=attempt==0?0.32:0.18;
            auto stats=comparison_windows::optimize_map(A,M,G,comp.edge,comp.polarity,permutation,
                cap,2400,28,0.7,0.70,0.0,0.6);
            mappingIterations+=stats.iterations;
        }
        comp.rebuild();
        des=std::make_unique<PaperDesign>(A,M,G);
        des->guardDesign=false;
        std::vector<std::vector<int>> samples(8,std::vector<int>(M));
        for(int s=0;s<8;s++){
            std::iota(samples[s].begin(),samples[s].end(),0);
            std::shuffle(samples[s].begin(),samples[s].end(),rng);
        }
        auto estimate=[&](U64 a,U64 b){
            double sum=0;
            for(int s=0;s<8;s++){
                sum+=comp.plan(samples[s],a,a^b).size();
                if(BARCODE_SYMMETRIC_ESTIMATE)sum+=comp.plan(samples[s],b,a^b).size();
            }
            return sum/(BARCODE_SYMMETRIC_ESTIMATE?16:8);
        };
        if(des->initialize([&](U64 a,U64 b){return comp.compatible(a,b);},estimate,[&](){return elapsed()>0.90;}))break;
        // Easier designs on retry; the final branch is valid for every input.
        if(attempt>=2 || elapsed()>0.85) return independent_bits(originalA,R);
        G=attempt==0?32:28;
    }
    if(elapsed()>1.0)return independent_bits(originalA,R);
    des->anneal(std::max(0.005,BARCODE_DESIGN_SECONDS-elapsed()),BARCODE_DESIGN_ITERS);
    std::vector<Paper> papers(K);
    std::vector<int> columns(K,-1),ded(P,-1);
    for(int i=0;i<M;i++)papers[i]={comp.opq[i],comp.black[i]};
    U64 opaque=PaperDesign::low(G);
    int next=M;
    for(int c=0;c<des->H;c++){
        opaque|=U64(1)<<des->handle[c];
        std::array<std::vector<int>,2> members;
        for(int x=0;x<des->U;x++)if(des->unit[x].c==c)
            members[des->color(des->unit[x],c)].push_back(x);
        for(auto& group:members)std::stable_sort(group.begin(),group.end(),[&](int x,int y){return des->weight(des->unit[x])<des->weight(des->unit[y]);});
        while(!members[0].empty()||!members[1].empty()){
            int color=members[1].size()>members[0].size();
            int x=members[color].back();members[color].pop_back();
            const auto& u=des->unit[x];
            U64 mask=opaque;if(u.b>=0)mask&=~(A[u.a]^A[u.b]);
            papers[next]={mask,A[u.a]&mask};columns[next]=c;
            ded[u.a]=next;if(u.b>=0)ded[u.b]=next;
            next++;
        }
    }
    if(next!=K||std::find(ded.begin(),ded.end(),-1)!=ded.end())return independent_bits(originalA,R);
    Solver solver(A);
    solver.M=M;solver.G=G;solver.H=des->H;solver.comparator=comp;
    solver.paper=papers;solver.col_of=columns;solver.ded=ded;solver.handle=des->handle;
    solver.hidx.assign(64,-1);
    for(int c=0;c<des->H;c++)solver.hidx[solver.handle[c]]=c;
    solver.gmask=PaperDesign::low(G);solver.hmask=~solver.gmask;
    solver.block_of.assign(K,-1);
    for(int i=0;i<M;i++)solver.block_of[i]=i;
    solver.h_opq.resize(K);solver.h_blk.resize(K);
    for(int k=0;k<K;k++){
        solver.h_opq[k]=solver.handle_bits(papers[k].opaque);
        solver.h_blk[k]=solver.handle_bits(papers[k].black);
    }
    auto pone=des->hole_probabilities();
    solver.bias_c.resize(des->H);solver.bias_g.resize(des->H);
    for(int c=0;c<des->H;c++)solver.bias_c[c]=pone[c]>.5,solver.bias_g[c]=std::abs(2*pone[c]-1);
    solver.order.resize(K);std::iota(solver.order.begin(),solver.order.end(),0);
    solver.init_cycles();
    solver.init_adaptive();

    std::string output;
    for(const auto& p:papers){
        std::string row(N,'.');
        for(int j=0;j<N;j++)row[permutation[j]]=!(p.opaque>>j&1)?'.':(p.black>>j&1)?'1':'0';
        output+=row+'\n';
    }
    std::cout<<output<<std::flush;
    double designTime=elapsed();
    long long total=0,errors=0,genericMoves=0;
    double queryTime=0;
    for(int r=0;r<R;r++){
        int u;if(!(std::cin>>u)||u==-1)return 0;
        double begin=elapsed();
        if(double(std::clock())/CLOCKS_PER_SEC>BARCODE_FAST_THRESHOLD)solver.fast_mode=true;
#ifdef BARCODE_FORCE_FAST
        solver.fast_mode=true;
#endif
#ifdef BARCODE_FORCE_FAST_ON_SPLIT
        // Validation only: enter the fallback from a genuinely interleaved
        // generic block, rather than from a conveniently normalized state.
        int generic_first=-1,generic_last=-1;
        for(int i=0;i<K;i++)if(solver.block_of[solver.order[i]]>=0){
            if(generic_first<0)generic_first=i;
            generic_last=i;
        }
        if(generic_last-generic_first+1!=M)solver.fast_mode=true;
#endif
        auto moves=solver.process(u);
        queryTime+=elapsed()-begin;
        output=std::to_string(moves.size())+'\n';
        for(auto [k,d]:moves){output+=std::to_string(k)+' '+std::to_string(d)+'\n';genericMoves+=k<M;}
        std::cout<<output<<std::flush;
        total+=moves.size();errors+=solver.display()!=A[u];
    }
    // Port: one `name = value` line per statistic (for scripts/observe.py stats).
    std::cerr << "moves = " << total << "\nerrors = " << errors
        << "\ngeneric = " << genericMoves << "\nM = " << M << "\nG = " << G
        << "\nmapping_iterations = " << mappingIterations << "\ndesign_iterations = " << des->iterations
        << "\ndesign_seconds = " << designTime << "\nquery_seconds = " << queryTime
        << "\nelapsed = " << elapsed() << "\nadaptive_fallbacks = " << solver.adaptive_failures
        << "\nfast_requests = " << solver.fast_requests
        << "\nevaluated_candidates = " << solver.evaluated_candidates
        << "\nduplicate_candidates = " << solver.duplicate_candidates
        << "\npost_saved = " << solver.postSaved
        << "\npost_changed = " << solver.postChanged
        << "\npost_candidates = " << solver.postCandidates
        << "\neject_trials = " << solver.ejectTrials
        << "\neject_changed = " << solver.ejectChanged
        << "\neject_saved = " << solver.ejectSaved
        << "\npost_split_states = " << solver.postSplitStates
        << "\npost_recoveries = " << solver.postRecoveries
        << "\nedge_replace_accepted = " << des->edgeReplaceAccepted
        << "\nemergency_design = 0\n";
    return 0;
}
