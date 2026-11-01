// Ported from other_agents/gpt6pro-07-barcode_solution_and_tests.zip (barcode_v1.cpp): <bits/stdc++.h> replaced by
// individual headers, stderr statistics printed as `name = value` lines.
// AHC074 / Layered Barcode Display, standalone C++20.
// Based on the comparison-paper / paired-dedicated-paper construction supplied
// in the question. The principal added optimization changes the final order:
//   * delete one or two operations after strict visibility replay;
//   * change reinsertion anchors for old main / old filler papers;
//   * retain the correct display and a recoverable generic-block invariant.
// Future requests are never inspected. Only one request is read per response.
//
// Build: g++ -std=c++20 -O2 -DNDEBUG barcode_solution.cpp -o barcode_solution
// Default: M=6, G=36, design budget=1.10s, postprocessing mode=5.
// Optional experiment arguments (normally omit all):
//   M G reserved0 reserved1 cpu_budget design_seconds top_penalty
//   future_weight patch_penalty post_mode
// BARCODE_FIXED_WORK: reproducible design iterations for ablation, not a
//                    machine-independent submission time limit.
// BARCODE_DISABLE_POST: ablation of the added operation-sequence optimization.
// BARCODE_FORCE_SIMPLE / BARCODE_FORCE_BITS: validate the safety paths.
//
// Performance is heuristic; no optimality or leaderboard-rank claim is made.

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
using U64 = uint64_t;
struct Random {
    U64 x=0x6176abcd1349ULL;
    U64 next(){x^=x<<7; x^=x>>9; return x;}
    int operator()(int n){return (static_cast<unsigned __int128>(next())*unsigned(n))>>64;}
    double real(){return (next()>>11)*0x1.0p-53;}
};
inline int pc(U64 x){return __builtin_popcountll(x);}
inline U64 low(int n){return n==64?~U64(0):(U64(1)<<n)-1;}

// Each window is a comparison between two generic sheets.
struct Comparator {
    int M=0,G=0;
    std::vector<std::pair<int,int>> edge;
    std::vector<int> polarity;
    std::vector<U64> opq,black;
    void init(int m,int g,Random& rng){
        M=m;G=g;
        std::vector<std::pair<int,int>> all;
        for(int a=0;a<M;a++)for(int b=a+1;b<M;b++)all.push_back({a,b});
        for(int i=int(all.size())-1;i>0;i--)std::swap(all[i],all[rng(i+1)]);
        edge.resize(G);polarity.resize(G);
        for(int j=0;j<G;j++){edge[j]=all[j%all.size()];polarity[j]=rng(2);}
        rebuild();
    }
    void rebuild(){
        opq.assign(M,0);black.assign(M,0);
        for(int j=0;j<G;j++){
            auto[a,b]=edge[j];U64 z=1ULL<<j;
            opq[a]|=z;opq[b]|=z;black[polarity[j]?a:b]|=z;
        }
    }
    std::array<unsigned,12> closure(U64 target,U64 holes)const{
        std::array<unsigned,12> r{};
        for(U64 s=holes&low(G);s;s&=s-1){
            int j=__builtin_ctzll(s);auto[a,b]=edge[j];
            if(int(target>>j&1)!=polarity[j])std::swap(a,b);
            r[a]|=1U<<b;
        }
        for(int k=0;k<M;k++)for(int a=0;a<M;a++)if(r[a]>>k&1)r[a]|=r[k];
        return r;
    }
    bool compatible(U64 a,U64 b)const{
        auto r=closure(a,a^b);
        for(int i=0;i<M;i++)if(r[i]>>i&1)return false;
        return true;
    }
    std::vector<std::pair<int,int>> plan(const std::vector<int>& cur,U64 target,U64 holes)const{
        auto r=closure(target,holes);
        for(int i=0;i<M;i++)if(r[i]>>i&1)return {{-1,-1}};
        std::array<unsigned,12> conflict{};
        bool satisfied=true;
        for(int i=0;i<M;i++)for(int j=0;j<i;j++)if(r[cur[i]]>>cur[j]&1){
            conflict[cur[i]]|=1U<<cur[j];conflict[cur[j]]|=1U<<cur[i];satisfied=false;
        }
        if(satisfied)return {};
        std::array<unsigned char,1<<12> valid{};valid[0]=1;
        unsigned kept=0;int count=-1,witness=-1,bottom=cur.back();unsigned bb=1U<<bottom;
        for(unsigned mask=1;mask<(1U<<M);mask++){
            unsigned rest=mask&(mask-1);int a=__builtin_ctz(mask);
            valid[mask]=valid[rest]&&!(rest&conflict[a]);if(!valid[mask])continue;
            int n=__builtin_popcount(mask);if(n<=count)continue;
            bool legal=mask&bb;int w=-1;
            if(!legal)for(int b=0;b<M;b++)if(!(mask>>b&1)&&b!=bottom&&!(r[b]&(mask|bb))){legal=true;w=b;break;}
            if(legal){kept=mask;count=n;witness=w;}
        }
        if(count<0)return {{-1,-1}};
        auto req=r;int last=-1;
        for(int a:cur)if(kept>>a&1){if(last>=0)req[last]|=1U<<a;last=a;}
        if(witness>=0){req[last]|=1U<<witness;req[bottom]|=1U<<witness;}
        std::array<unsigned,12> pred{};
        for(int a=0;a<M;a++)for(int b=0;b<M;b++)if(req[a]>>b&1)pred[b]|=1U<<a;
        std::vector<int> goal;unsigned placed=0;
        for(int t=0;t<M;t++){
            int a=-1;for(int b:cur)if(!(placed>>b&1)&&!(pred[b]&~placed)){a=b;break;}
            if(a<0)return {{-1,-1}};goal.push_back(a);placed|=1U<<a;
        }
        std::vector<int> ord=cur;std::vector<std::pair<int,int>> moves;
        for(int a:cur)if(!(kept>>a&1)){
            U64 cover=0;for(int b:ord){if(a==b)break;cover|=opq[b];}
            if(!(opq[a]&~cover))return {{-1,-1}};
            int successor=-1;bool passed=false;
            for(int b:goal){if(passed&&(kept>>b&1)){successor=b;break;}if(b==a)passed=true;}
            int old=std::find(ord.begin(),ord.end(),a)-ord.begin();ord.erase(ord.begin()+old);
            int d=successor<0?M-1:std::find(ord.begin(),ord.end(),successor)-ord.begin();
            ord.insert(ord.begin()+d,a);if(old!=d)moves.push_back({a,d});kept|=1U<<a;
        }
        return moves;
    }
};

inline U64 closure8(U64 r,int m){
    for(int k=0;k<m;k++)r|=((r>>k)&0x0101010101010101ULL)*((r>>(8*k))&255);
    return r;
}
// Anneal the assignment of physical windows to comparison edges.
inline void optimize_map(std::vector<U64>& A,Comparator& co,std::vector<int>& permutation,double seconds){
    int m=co.M,g=co.G;if(m>8||g>=64||g<m*(m-1)/2)return;
    auto start=std::chrono::steady_clock::now();Random rng;
    int ix[8][8];std::vector<std::pair<int,int>> ep;
    for(int a=0;a<m;a++)for(int b=a+1;b<m;b++){ix[a][b]=ix[b][a]=ep.size();ep.push_back({a,b});}
    int ne=ep.size();std::vector<U64> masks(ne),fwd(ne),rev(ne);
    std::vector<int> which(64,-1),counts(ne),order(64);std::iota(order.begin(),order.end(),0);
    U64 pol=0;
    for(int e=0;e<ne;e++){auto[a,b]=ep[e];fwd[e]=1ULL<<(8*a+b);rev[e]=1ULL<<(8*b+a);}
    for(int j=0;j<g;j++){
        auto[a,b]=co.edge[j];int e=ix[a][b];which[j]=e;masks[e]|=1ULL<<j;counts[e]++;
        int c=co.polarity[j]^(a>b);if(c)pol|=1ULL<<j;
    }
    struct Pair{U64 au,diff,dir;int u,v;double base,w;};
    std::vector<Pair> pairs;std::vector<double> degree(A.size());
    for(int u=0;u<256;u++)for(int v=u+1;v<256;v++){
        U64 d=A[u]^A[v];int h=pc(d);if(h>28)continue;
        U64 r=0,z=A[u]^pol;
        for(int e=0;e<ne;e++){U64 q=d&masks[e];if(q&~z)r|=fwd[e];if(q&z)r|=rev[e];}
        bool ok=!(closure8(r,m)&0x8040201008040201ULL);
        double base=std::exp((24*(1-0.30*g/64.0)-h+0.30*pc(d&low(g)))*0.35);
        double w=ok?base:0;pairs.push_back({A[u],d,r,u,v,base,w});degree[u]+=w;degree[v]+=w;
    }
    auto value=[](double d){return std::pow(d+0.2,0.7);};
    double score=0;for(double d:degree)score+=value(d);double best=score;
    auto bm=masks;auto bo=order;U64 bp=pol;
    std::vector<U64> ndir(pairs.size());std::vector<double> nbase(pairs.size()),nw(pairs.size()),delta(256);
    std::vector<int> changed;double elapsed=0;
    for(int it=0;;it++){
        if((it&15)==0){
#ifdef BARCODE_FIXED_WORK
            elapsed=double(it)/2400*seconds;if(it>=2400)break;
#else
            elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();if(elapsed>=seconds)break;
#endif
        }
        int ia=rng(g),ib=rng(g),a=order[ia],b=order[ib];bool window=rng.real()<0.6;
        if(window){ib=g+rng(64-g);b=order[ib];}
        int kind=rng(10),ea=which[a],eb=window?ea:which[b];
        U64 oa=masks[ea],ob=masks[eb],opol=pol,aff=0;int transfer=-1;
        if(window){masks[ea]^=(1ULL<<a)|(1ULL<<b);pol=(pol&~(1ULL<<b))|((opol>>a&1)<<b);aff=(1ULL<<a)|(1ULL<<b);}
        else if(kind<3){pol^=1ULL<<a;aff=1ULL<<a;eb=ea;ob=oa;}
        else if(kind<8){if(ea==eb)continue;masks[ea]^=(1ULL<<a)|(1ULL<<b);masks[eb]^=(1ULL<<a)|(1ULL<<b);aff=(1ULL<<a)|(1ULL<<b);}
        else{if(counts[ea]<2)continue;eb=rng(ne);if(ea==eb)continue;ob=masks[eb];masks[ea]^=1ULL<<a;masks[eb]|=1ULL<<a;transfer=eb;aff=1ULL<<a;}
        U64 erase=fwd[ea]|rev[ea]|fwd[eb]|rev[eb];std::fill(delta.begin(),delta.end(),0);changed.clear();
        for(int p=0;p<int(pairs.size());p++){
            auto&q=pairs[p];if(!(q.diff&aff))continue;U64 r=q.dir&~erase,z=q.au^pol;
            U64 d=q.diff&masks[ea];if(d&~z)r|=fwd[ea];if(d&z)r|=rev[ea];
            d=q.diff&masks[eb];if(d&~z)r|=fwd[eb];if(d&z)r|=rev[eb];
            double base=q.base;if(window)base*=std::exp(0.105*(int(q.diff>>b&1)-int(q.diff>>a&1)));
            if(r==q.dir&&base==q.base)continue;
            double w=(closure8(r,m)&0x8040201008040201ULL)?0:base;
            ndir[p]=r;nbase[p]=base;nw[p]=w;changed.push_back(p);delta[q.u]+=w-q.w;delta[q.v]+=w-q.w;
        }
        double ds=0;for(int u=0;u<256;u++)if(std::abs(delta[u])>1e-9)ds+=value(std::max(0.0,degree[u]+delta[u]))-value(degree[u]);
        double temp=0.2*std::pow(0.005/0.2,elapsed/seconds);
        if(ds>=0||rng.real()<std::exp(ds/temp)){
            score+=ds;for(int p:changed){pairs[p].dir=ndir[p];pairs[p].base=nbase[p];pairs[p].w=nw[p];}
            for(int u=0;u<256;u++)degree[u]=std::max(0.0,degree[u]+delta[u]);
            if(window){which[a]=-1;which[b]=ea;std::swap(order[ia],order[ib]);}
            else{if(kind>=3&&kind<8)std::swap(which[a],which[b]);if(transfer>=0){counts[ea]--;counts[eb]++;which[a]=eb;}}
            if(score>best){best=score;bm=masks;bp=pol;bo=order;}
        }else{masks[ea]=oa;masks[eb]=ob;pol=opol;}
    }
    for(int j=0;j<g;j++){int x=bo[j],e=0;while(e<ne&&!(bm[e]>>x&1))e++;co.edge[j]=ep[e];co.polarity[j]=bp>>x&1;}
    auto oldp=permutation;for(int j=0;j<64;j++)permutation[j]=oldp[bo[j]];
    for(U64& a:A){U64 b=0;for(int j=0;j<64;j++)b|=(a>>bo[j]&1)<<j;a=b;}
    co.rebuild();
}

struct PaperDesign{
    struct Unit{int a=-1,b=-1,c=-1;};
    Random rng;
    int M,G,H,U,need;
    std::vector<U64> A,hb;
    std::vector<int> handle,owner;
    std::vector<Unit> unit;
    std::vector<std::vector<int>> partners;
    uint8_t ok[256][256]{};
    float gcost[256][256]{};
    std::vector<int> nc,nt,n1,pairOne;
    std::vector<std::array<int,2>> hn;
    double cur=0,holeWeight=0.50,digWeight=1.0,rankPriority=0.85;
    PaperDesign(const std::vector<U64>& a,int m,int g):M(m),G(g),H(64-g),U(192-m),need(256-U),A(a){
        handle.resize(H);std::iota(handle.begin(),handle.end(),G);
        hb.resize(256);for(int i=0;i<256;i++)hb[i]=A[i]>>G;
        owner.assign(256,-1);partners.resize(256);nc.resize(H);nt.resize(H);n1.resize(H);pairOne.resize(H);hn.resize(H);
    }
    bool valid(const Unit&u,int c)const{return u.b<0||((hb[u.a]^hb[u.b])>>c&1)==0;}
    int color(const Unit&u,int c)const{return hb[u.a]>>c&1;}
    int weight(const Unit&u)const{return u.b<0?1:2;}
    U64 holes(const Unit&u)const{return (low(H)&~low(u.c+1))|(u.b<0?0:hb[u.a]^hb[u.b]);}
    double colcost(int c)const{
        int imbalance=std::max(0,std::abs(nc[c]-2*n1[c])-1);
        int p=nt[c]-nc[c],p1=pairOne[c],p0=p-p1;
        double base=nt[c]*(nc[c]-1)*0.5;
        int fp=n1[c]>nc[c]-n1[c]?p1:n1[c]<nc[c]-n1[c]?p0:std::max(p0,p1);
        double alt=nc[c]*(nc[c]-1)*0.5+p0*p0+p1*p1-fp;
        return digWeight*(base-rankPriority*std::max(0.0,base-alt))+5.0*imbalance*imbalance+((n1[c]==0||n1[c]==nc[c])?100000.0:0.0);
    }
    double hcost(int j)const{int x=hn[j][0],y=hn[j][1];return x+y?holeWeight*4.0*x*y/(x+y):0;}
    double gc(const Unit&u)const{return u.b<0?0:2*gcost[u.a][u.b];}
    void update(const Unit&u,int s){
        cur-=colcost(u.c);nc[u.c]+=s;nt[u.c]+=s*weight(u);n1[u.c]+=s*color(u,u.c);if(u.b>=0)pairOne[u.c]+=s*color(u,u.c);
        cur+=colcost(u.c);
        for(U64 z=holes(u);z;z&=z-1){int j=__builtin_ctzll(z);cur-=hcost(j);hn[j][hb[u.a]>>j&1]+=s;if(u.b>=0)hn[j][hb[u.b]>>j&1]+=s;cur+=hcost(j);}
        cur+=s*gc(u);
    }
    void rebuild(){
        std::fill(nc.begin(),nc.end(),0);std::fill(nt.begin(),nt.end(),0);std::fill(n1.begin(),n1.end(),0);std::fill(pairOne.begin(),pairOne.end(),0);std::fill(hn.begin(),hn.end(),std::array<int,2>{0,0});
        cur=0;for(int c=0;c<H;c++)cur+=colcost(c);for(auto&u:unit)update(u,1);
        for(int x=0;x<U;x++){owner[unit[x].a]=x;if(unit[x].b>=0)owner[unit[x].b]=x;}
    }
    bool initialize(const Comparator& comp,const std::function<bool()>& expired={}){
        struct E{double w;int a,b;};std::vector<E> edges;
        std::vector<std::vector<int>> samples(4,std::vector<int>(M));
        for(auto&s:samples){std::iota(s.begin(),s.end(),0);for(int i=M-1;i>0;i--)std::swap(s[i],s[rng(i+1)]);}
        for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){
            if((b&31)==0&&expired&&expired())return false;
            if(!comp.compatible(A[a],A[b]))continue;
            ok[a][b]=ok[b][a]=1;partners[a].push_back(b);partners[b].push_back(a);
            float sum=0;for(auto&s:samples)sum+=comp.plan(s,A[a],A[a]^A[b]).size();sum/=samples.size();
            gcost[a][b]=gcost[b][a]=sum;
            U64 d=A[a]^A[b];edges.push_back({0.65*pc(d>>G)+2*sum+0.04*pc(d),a,b});
        }
        std::sort(edges.begin(),edges.end(),[](auto&a,auto&b){return a.w<b.w;});
        std::vector<bool> used(256);
        for(auto&e:edges){if(int(unit.size())==need)break;if(used[e.a]||used[e.b])continue;used[e.a]=used[e.b]=true;unit.push_back({e.a,e.b,-1});}
        auto cost=[&](int a,int b){U64 d=A[a]^A[b];return 0.65*pc(d>>G)+2*gcost[a][b]+0.04*pc(d);};
        while(int(unit.size())<need){
            double best=1e100;int bx=-1,bu=-1,bv=-1,bf=0;
            for(int x=0;x<int(unit.size());x++)for(int f=0;f<2;f++){
                if(expired&&expired())return false;
                int a=f?unit[x].b:unit[x].a,b=f?unit[x].a:unit[x].b;
                for(int u:partners[a])if(!used[u])for(int v:partners[b])if(!used[v]&&u!=v){double z=cost(a,u)+cost(b,v)-cost(a,b);if(z<best){best=z;bx=x;bu=u;bv=v;bf=f;}}
            }
            if(bx<0)return false;
            int a=bf?unit[bx].b:unit[bx].a,b=bf?unit[bx].a:unit[bx].b;
            unit[bx]={a,bu,-1};unit.push_back({b,bv,-1});used[bu]=used[bv]=true;
        }
        for(int a=0;a<256;a++)if(!used[a])unit.push_back({a,-1,-1});
        std::vector<int> perm(U);std::iota(perm.begin(),perm.end(),0);for(int i=U-1;i>0;i--)std::swap(perm[i],perm[rng(i+1)]);
        auto take=[&](int c,int colorWanted,bool pairFirst){
            for(int pass=0;pass<2;pass++)for(int x:perm){auto&u=unit[x];if(u.c>=0||(u.b>=0)!=(pairFirst^(pass!=0))||!valid(u,c)||color(u,c)!=colorWanted)continue;u.c=c;nc[c]++;n1[c]+=colorWanted;return true;}return false;
        };
        for(int c=0;c<H;c++)for(int v=0;v<2;v++)if(!take(c,v,false))return false;
        std::vector<int> cap(H,2);int total=H*2;
        while(total+2<=U){int c=0;double z=1e100;for(int j=0;j<H;j++)if((cap[j]+1.0)/(j+1.5)<z){z=(cap[j]+1.0)/(j+1.5);c=j;}cap[c]+=2;total+=2;}
        for(int c=H-1;c>=0;c--)while(nc[c]<cap[c]){int v=2*n1[c]<nc[c]?1:0;if(!take(c,v,true)&&!take(c,v^1,true))break;}
        for(auto&u:unit)if(u.c<0){
            int best=-1;double z=1e100;
            for(int c=0;c<H;c++)if(valid(u,c)){double q=weight(u)*(nc[c]*0.5+0.5*(H-1-c))+nc[c]*0.5+3*std::abs(nc[c]+1-2*(n1[c]+color(u,c)));if(q<z){z=q;best=c;}}
            if(best<0)return false;u.c=best;nc[best]++;n1[best]+=color(u,best);
        }
        rebuild();return true;
    }
    void anneal(double seconds){
        auto start=std::chrono::steady_clock::now();double progress=0,temp=2;
        auto accept=[&](double d){return d<=0||rng.real()<std::exp(-d/temp);};
        auto best=unit;auto bh=handle;double bc=cur;
        for(int it=0;;it++){
            if((it&255)==0){
#ifdef BARCODE_FIXED_WORK
                progress=double(it)/1600000;
#else
                progress=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()/seconds;
#endif
                if(progress>=1)break;temp=2*std::pow(0.015/2.0,progress);
            }
            int type=rng(1000);
            if(type<5){
                int a=rng(H),b=rng(H);if(a==b)continue;bool validSwap=true;
                for(auto&u:unit)if(u.b>=0&&(u.c==a||u.c==b)){int j=u.c==a?b:a;if((hb[u.a]^hb[u.b])>>j&1){validSwap=false;break;}}
                if(!validSwap)continue;double old=cur;
                auto sw=[&](){std::swap(handle[a],handle[b]);for(auto&h:hb)if(((h>>a)^(h>>b))&1)h^=(1ULL<<a)|(1ULL<<b);};
                sw();rebuild();if(!accept(cur-old)){sw();rebuild();}
            }else{
                int x=rng(U),y=rng(U);if(x==y)continue;Unit nx=unit[x],ny=unit[y];
                if(type<430){
                    if(nx.b<0){std::swap(x,y);nx=unit[x];ny=unit[y];if(nx.b<0)continue;}
                    int ix=rng(2),iy=ny.b<0?0:rng(2);
                    if(type<380){int f=ix==0?nx.b:nx.a;auto&p=partners[f];if(p.empty())continue;int n=p[rng(p.size())];y=owner[n];if(x==y)continue;ny=unit[y];iy=ny.a==n?0:1;}
                    int&a=ix==0?nx.a:nx.b;int&b=iy==0?ny.a:ny.b;std::swap(a,b);
                }else if(type<750){if(nx.c==ny.c)continue;std::swap(nx.c,ny.c);}
                else if(type<900){if(nx.c==ny.c||nc[nx.c]<=2)continue;nx.c=ny.c;}
                else{
                    int c=nx.c,d=ny.c;if(c==d||nc[c]<=2)continue;int z=-1;
                    for(int t=0;t<16;t++){int j=rng(U);if(j!=x&&unit[j].c==c&&color(unit[j],c)!=color(nx,c)){z=j;break;}}
                    if(z<0)continue;y=z;ny=unit[y];nx.c=ny.c=d;
                }
                if(!valid(nx,nx.c)||!valid(ny,ny.c)||(nx.b>=0&&!ok[nx.a][nx.b])||(ny.b>=0&&!ok[ny.a][ny.b]))continue;
                Unit ox=unit[x],oy=unit[y];double old=cur;update(ox,-1);update(oy,-1);update(nx,1);update(ny,1);
                if(accept(cur-old)){unit[x]=nx;unit[y]=ny;owner[nx.a]=x;if(nx.b>=0)owner[nx.b]=x;owner[ny.a]=y;if(ny.b>=0)owner[ny.b]=y;}
                else{update(nx,-1);update(ny,-1);update(ox,1);update(oy,1);cur=old;}
            }
            if(cur<bc-1e-7){bc=cur;best=unit;bh=handle;}
        }
        unit=best;handle=bh;for(int i=0;i<256;i++){hb[i]=0;for(int j=0;j<H;j++)hb[i]|=(A[i]>>handle[j]&1)<<j;}rebuild();
    }
};

struct Paper{U64 opaque=0,black=0;};
struct Solver{
    int M,G,H;
    Comparator comp;
    std::vector<U64>A;
    std::vector<Paper> paper;
    std::vector<int> col,handle,ded,order,weight;
    std::vector<std::array<double,2>> holes;
    std::vector<std::pair<int,int>> moves;
    bool invalid=false;
    int main=-1;
    double topPenalty=0.15,futureWeight=0.60,patchPenalty=0.80;
#ifdef BARCODE_DISABLE_POST
    int postMode=0;
#else
    int postMode=5;
#endif
    long long postSaved=0,postChanged=0,postCandidates=0,jointUsed=0;
    struct State{std::vector<int> order;int main;};
    State state()const{return {order,main};}
    void restore(const State&s){order=s.order;main=s.main;moves.clear();invalid=false;}
    int pos(int k)const{return std::find(order.begin(),order.end(),k)-order.begin();}
    bool visible(int k)const{U64 covered=0;for(int x:order){if(k==x)return paper[k].opaque&~covered;covered|=paper[x].opaque;}return false;}
    U64 display()const{U64 covered=0,result=0;for(int k:order){result|=paper[k].black&~covered;covered|=paper[k].opaque;}return result;}
    void move(int k,int d){
        int p=pos(k);if(p==d)return;
        if(p>=192||d<0||d>=192||!visible(k)){invalid=true;return;}
        order.erase(order.begin()+p);order.insert(order.begin()+d,k);moves.push_back({k,d});
    }
    std::vector<char> outliers(bool includeMain=true)const{
        std::vector<char> bad(192);int cur=H;bool gen=false;
        for(int i=191;i>=0;i--){int k=order[i];if(col[k]<0){gen=true;continue;}
            if(k==main){if(includeMain)bad[k]=true;continue;}
            if(gen||col[k]>cur)bad[k]=true;else cur=col[k];
        }
        return bad;
    }
    double future()const{
        auto extra=outliers();std::vector<int> rank(H);std::vector<std::array<int,2>> first(H,{1000,1000});
        std::vector<std::array<bool,2>> available(H,{false,false});double val=0;
        for(int k:order)if(col[k]>=0){
            int c=col[k],v=paper[k].black>>handle[c]&1;
            if(extra[k]){available[c][v]=true;continue;}
            first[c][v]=std::min(first[c][v],rank[c]);val+=weight[k]*rank[c]/256.0;rank[c]++;
        }
        for(int c=0;c<H;c++)for(int v=0;v<2;v++)if(!available[c][v])val+=holes[c][v]*std::min(rank[c],first[c][v]);
        return val;
    }
    void insert_home(int k,int u,int barrier=-1){
        int c=col[k],color=paper[k].black>>handle[c]&1;
        auto extra=outliers();std::vector<int> v;
        for(int x:order)if(x!=k&&col[x]==c&&!extra[x])v.push_back(x);
        if(barrier>=0&&std::find(v.begin(),v.end(),barrier)==v.end()){invalid=true;return;}
        int n=v.size(),lo=barrier<0?0:std::find(v.begin(),v.end(),barrier)-v.begin()+1;
        std::vector<double> suffix(n+1);std::array<int,2> first={n,n};
        for(int i=n-1;i>=0;i--){suffix[i]=suffix[i+1]+weight[v[i]];first[paper[v[i]].black>>handle[c]&1]=i;}
        bool need=u>=0&&!(paper[ded[u]].opaque>>handle[c]&1);int wanted=u<0?0:A[u]>>handle[c]&1;
        int gap=n;double best=1e100;
        for(int i=lo;i<=n;i++){
            std::array<int,2> f;for(int v=0;v<2;v++){f[v]=first[v]+(first[v]>=i);if(v==color)f[v]=std::min(f[v],i);}
            double value=(weight[k]*i+suffix[i])/256.0+holes[c][0]*f[0]+holes[c][1]*f[1];
            if(need&&barrier<0)value+=f[wanted];
            if(k==main&&i==0&&n)value+=topPenalty;
            value+=1e-7*(n-i);if(value<best){best=value;gap=i;}
        }
        int d;
        if(n){int anchor=gap<n?v[gap]:v.back();d=pos(anchor)+(gap==n);if(pos(k)<d)d--;}
        else{
            d=192;for(int i=0;i<192;i++){int x=order[i];if(x!=k&&col[x]>=c&&!extra[x]){d=i;break;}}
            if(pos(k)<d)d--;
        }
        move(k,d);if(k==main)main=-1;
    }
    void cleanup(int u){
        for(int count=0;count<192;count++){
            auto extra=outliers();bool any=false;int x=-1;
            for(int k:order)if(extra[k]){any=true;if(visible(k)){x=k;break;}}
            if(!any)return;if(x<0){invalid=true;return;}insert_home(x,u);if(invalid)return;
        }
        invalid=true;
    }
    void cleanup_reuse(int u,int mode){
        if(mode==0){cleanup(u);return;}
        int d=ded[u],cd=col[d];U64 need=~paper[d].opaque&~low(G);
        auto extra=outliers();std::vector<char> keep(192);std::vector<int> level(192,-1);
        int next=H,genlast=-1;
        for(int i=0;i<192;i++)if(col[order[i]]<0)genlast=i;
        for(int i=191;i>=0;i--){int k=order[i];if(col[k]<0)continue;if(!extra[k])next=col[k];else level[k]=next;}
        for(int k:order)if(extra[k]&&k!=main&&k!=d&&pos(k)>genlast){
            int l=level[k],c=col[k];bool safe=true;U64 covered=0;
            for(int j=l;j<=c;j++)if(paper[k].opaque>>handle[j]&1){
                if(j==cd)safe=false;
                U64 b=1ULL<<handle[j];if(need&b){if((paper[k].black^A[u])&b)safe=false;else covered|=b;}
            }
            if(safe&&covered)keep[k]=1;
        }
        int old=main,oldLevel=-1;
        if(mode>=2&&old>=0&&old!=d){
            int l=0,c=col[old];
            for(int j=0;j<=c;j++)if((paper[old].opaque&need&(paper[old].black^A[u]))>>handle[j]&1)l=j+1;
            if(c>=cd&&(paper[old].opaque>>handle[cd]&1))l=std::max(l,cd+1);
            U64 covered=0;for(int j=l;j<=c;j++)covered|=need&paper[old].opaque&(1ULL<<handle[j]);
            if(covered&&l<c)oldLevel=l;
        }
        if(old>=0&&visible(old)){
            if(oldLevel>=0){
                int destination=192;auto bad=outliers();
                for(int i=0;i<192;i++){int k=order[i];if(k!=old&&col[k]>=oldLevel&&!bad[k]){destination=i;break;}}
                if(pos(old)<destination)destination--;move(old,destination);main=-1;keep[old]=1;
            }else insert_home(old,u);
        }
        for(int it=0;it<192;it++){
            auto bad=outliers();int x=-1;bool remaining=false;
            for(int k:order)if(bad[k]&&!keep[k]){remaining=true;if(visible(k)){x=k;break;}}
            if(!remaining)return;
            bool forcedReturn=x<0;
            if(x<0){
                // A kept patch may conceal another old patch: return it first.
                for(int k:order)if(bad[k]&&visible(k)){x=k;keep[k]=0;break;}
            }
            if(x<0){invalid=true;return;}
            if(mode>=3&&x!=d&&!forcedReturn){
                int c=col[x],l=0;
                for(int j=0;j<=c;j++)if((paper[x].opaque&need&(paper[x].black^A[u]))>>handle[j]&1)l=j+1;
                if(c>=cd&&(paper[x].opaque>>handle[cd]&1))l=std::max(l,cd+1);
                U64 cov=0;for(int j=l;j<=c;j++)cov|=need&paper[x].opaque&(1ULL<<handle[j]);
                if(cov&&l<c){
                    int destination=192;auto currentBad=outliers();
                    for(int i=0;i<192;i++){int k=order[i];if(k!=x&&col[k]>=l&&!currentBad[k]){destination=i;break;}}
                    if(pos(x)<destination)destination--;move(x,destination);if(x==main)main=-1;keep[x]=1;
                    if(invalid)return;continue;
                }
            }
            insert_home(x,u);if(invalid)return;
        }
        invalid=true;
    }
    void set_generic(int u){
        int begin=0;while(begin<192&&col[order[begin]]>=0)begin++;
        if(begin+M>192){invalid=true;return;}
        std::vector<int> cur;for(int i=begin;i<begin+M;i++){if(col[order[i]]>=0){invalid=true;return;}cur.push_back(order[i]);}
        auto ops=comp.plan(cur,A[u],~paper[ded[u]].opaque);
        for(auto[k,d]:ops){if(k<0){invalid=true;return;}move(k,begin+d);if(invalid)return;}
    }
    int column_top(int c)const{auto bad=outliers();for(int k:order)if(col[k]==c&&!bad[k])return k;return -1;}
    void expose(int d,int u){
        int c=col[d];for(int t=0;column_top(c)!=d;t++){
            int x=column_top(c);if(t>=192||x<0){invalid=true;return;}insert_home(x,u,d);if(invalid)return;
        }
    }
    void fix(int u){
        U64 diff=(display()^A[u]);
        for(int c=0;c<H;c++)if(diff>>handle[c]&1){
            for(int t=0;;t++){
                int k=column_top(c);if(k<0||t>=192){invalid=true;return;}
                if(int(paper[k].black>>handle[c]&1)==int(A[u]>>handle[c]&1))break;
                int barrier=-1;auto bad=outliers();
                for(int x:order)if(col[x]==c&&!bad[x]&&int(paper[x].black>>handle[c]&1)==int(A[u]>>handle[c]&1)){barrier=x;break;}
                if(barrier<0){invalid=true;return;}insert_home(k,u,barrier);if(invalid)return;
            }
        }
    }
    void greedy_patches(int u,int d,int depthLimit){
        // Non-overlapping safe patches provide a cheap deterministic fallback.
        U64 holeAll=~paper[d].opaque&~low(G),wanted=holeAll;auto bad=outliers();
        U64 cov=0;for(int k:order){if(bad[k])wanted&=~(paper[k].opaque&~cov);cov|=paper[k].opaque;}
        std::vector<int> oldLevels;int nextLevel=H;
        for(int i=191;i>=0;i--){int k=order[i];if(col[k]<0)continue;if(!bad[k])nextLevel=col[k];else oldLevels.push_back(nextLevel);}
        auto conflicts=[&](int l,int c){for(int level:oldLevels)if(level>l&&c>=level)return true;return false;};
        std::vector<std::vector<int>> qs(H);for(int k:order)if(col[k]>=0&&!bad[k]&&k!=d)qs[col[k]].push_back(k);
        std::vector<int> fc(H);
        for(int c=0;c<H;c++)if(wanted>>handle[c]&1){for(int k:qs[c]){if(int(paper[k].black>>handle[c]&1)==int(A[u]>>handle[c]&1))break;fc[c]++;}}
        struct Cand{int c=-1,k=-1,l=0,depth=0;bool post=false;double gain=0;int c2=-1,k2=-1,depth2=0;bool post2=false;};
        std::vector<double> best(H+1);std::vector<Cand> pick(H+1);
        struct PC{int c,k,depth;U64 opaque,shown,bad;bool ownHole;int sum;};
        auto hb=[&](U64 x){return x>>G;};
        U64 neededBits=hb(wanted),targetBits=hb(A[u]);
        std::vector<PC> pcs;
        for(int c=0;c<H;c++)if(c!=col[d]&&!qs[c].empty()&&visible(qs[c][0])){
            for(int dep=0;dep<int(qs[c].size())&&dep<=depthLimit;dep++){
                int k=qs[c][dep];U64 opq=hb(paper[k].opaque)&low(c+1),shown=opq&neededBits;
                int sum=0;for(U64 z=shown;z;z&=z-1)sum+=fc[__builtin_ctzll(z)];
                pcs.push_back({c,k,dep,opq,shown,shown&(hb(paper[k].black)^targetBits),bool(holeAll>>handle[c]&1),sum});
            }
        }
        auto high=[](U64 x){return x?63-__builtin_clzll(x):-1;};
        for(int c=0;c<H;c++){
            best[c+1]=best[c];if(c==col[d]||qs[c].empty()||!visible(qs[c][0]))continue;
            for(int dep=0;dep<int(qs[c].size())&&dep<=depthLimit;dep++){
                int k=qs[c][dep],l=0;
                U64 wrong=(paper[k].black^A[u])&paper[k].opaque&wanted;
                for(int j=0;j<=c;j++)if(wrong>>handle[j]&1)l=j+1;
                if(l>c)continue;
                for(int lv=l;lv<=c;lv++){
                    if(conflicts(lv,c))continue;
                    bool post=c>col[d]&&lv<=col[d]&&(paper[k].opaque>>handle[col[d]]&1);
                    if(post&&!(holeAll>>handle[c]&1))continue;
                    int save=0;for(int j=lv;j<=c;j++)if((paper[k].opaque&wanted)>>handle[j]&1)if(j!=c||dep)save+=fc[j];
                    double gain=save-dep-1.0-patchPenalty;
                    if(best[lv]+gain>best[c+1]){best[c+1]=best[lv]+gain;pick[c+1]={c,k,lv,dep,post,gain};}
                }
            }
            for(auto&L:pcs)if(L.c==c&&L.bad){
                for(auto&U:pcs){
                    if(U.c>=c||U.c<high(L.bad)||U.sum+L.sum<5+U.depth+L.depth)continue;
                    int a=std::max(high(U.bad),high(L.bad&~U.opaque))+1;if(a>U.c||conflicts(a,c))continue;
                    bool postU=U.c>col[d]&&a<=col[d]&&(U.opaque>>col[d]&1);
                    bool postL=postU||(L.c>col[d]&&a<=col[d]&&(L.opaque>>col[d]&1));
                    if((postU&&!U.ownHole)||(postL&&!L.ownHole))continue;
                    U64 cu=U.shown&~low(a),cl=L.shown&~U.opaque&~low(a);
                    if(U.depth==0&&U.ownHole)cu&=~(1ULL<<U.c);if(L.depth==0&&L.ownHole)cl&=~(1ULL<<L.c);
                    int save=0;for(U64 z=cu|cl;z;z&=z-1)save+=fc[__builtin_ctzll(z)];
                    double gain=save-U.depth-L.depth-2.0-2*patchPenalty;
                    if(best[a]+gain>best[c+1]){best[c+1]=best[a]+gain;pick[c+1]={c,L.k,a,L.depth,postL,gain,U.c,U.k,U.depth,postU};}
                }
            }
        }
        std::vector<Cand> selected;for(int c=H;c>0;){if(pick[c].k<0)c--;else{selected.push_back(pick[c]);c=pick[c].l;}}
        std::reverse(selected.begin(),selected.end());
        std::vector<Cand> expanded;
        for(auto&p:selected){if(p.k2>=0)expanded.push_back({p.c2,p.k2,p.l,p.depth2,p.post2,0});expanded.push_back(p);}
        selected.swap(expanded);
        auto put=[&](const Cand&p){
            expose(p.k,u);if(invalid)return;
            auto bad=outliers();int dest=192;
            for(int i=0;i<192;i++){int k=order[i];if(k!=p.k&&col[k]>=p.l&&!bad[k]){dest=i;break;}}
            if(pos(p.k)<dest)dest--;move(p.k,dest);
        };
        for(auto&p:selected)if(!p.post){put(p);if(invalid)return;}
        move(d,0);main=d;if(invalid)return;
        for(auto&p:selected)if(p.post){put(p);if(invalid)return;}
        fix(u);
    }
    std::vector<std::pair<int,int>> post_optimize(const State& initial,std::vector<std::pair<int,int>> ops,int u){
        if(postMode==0||ops.empty())return ops;
        struct Edit{int k,anchor;};
        auto anchorize=[&](const std::vector<std::pair<int,int>>& src){
            auto ord=initial.order;std::vector<Edit> edits;
            for(auto[k,d]:src){int p=std::find(ord.begin(),ord.end(),k)-ord.begin();ord.erase(ord.begin()+p);edits.push_back({k,d?ord[d-1]:-1});ord.insert(ord.begin()+d,k);}
            return edits;
        };
        auto edits=anchorize(ops);
        std::vector<char> initialExtra(192);int backColumn=H;bool pastGeneric=false;
        for(int z=191;z>=0;z--){int k=initial.order[z];if(col[k]<0){pastGeneric=true;continue;}if(k==initial.main){initialExtra[k]=true;continue;}if(pastGeneric||col[k]>backColumn)initialExtra[k]=true;else backColumn=col[k];}
        State bestState=state();auto bestOps=ops;double bestScore;
        auto score=[&](size_t count){auto extra=outliers(false);return count+patchPenalty*std::count(extra.begin(),extra.end(),1)+futureWeight*future();};
        bestScore=score(ops.size());
        auto evaluate=[&](const std::vector<Edit>& trial){
            ++postCandidates;
            std::vector<int> ord=initial.order;std::vector<std::pair<int,int>> path;
            for(auto [k,a]:trial){
                int p=std::find(ord.begin(),ord.end(),k)-ord.begin();
                int dest=a<0?0:int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;
                if(a==k)return false;
                if(p<dest)--dest;
                if(p==dest)continue;
                U64 covered=0;for(int i=0;i<p;i++)covered|=paper[ord[i]].opaque;
                if(!(paper[k].opaque&~covered))return false;
                ord.erase(ord.begin()+p);ord.insert(ord.begin()+dest,k);path.push_back({k,dest});
            }
            U64 covered=0,shown=0;int first=-1,last=-1,count=0;
            for(int i=0;i<192;i++){int k=ord[i];shown|=paper[k].black&~covered;covered|=paper[k].opaque;if(col[k]<0){if(first<0)first=i;last=i;count++;}}
            if(shown!=A[u]||count!=M||last-first+1!=M)return false;
            order=ord;main=col[order[0]]>=0?order[0]:-1;
            double value=score(path.size());
            if(value+1e-8<bestScore){bestScore=value;bestOps=std::move(path);bestState=state();return true;}
            return false;
        };
        bool changed=false;
        for(int pass=0;pass<3;pass++){
            bool any=false;
            for(int i=int(edits.size())-1;i>=0;i--){
                auto trial=edits;trial.erase(trial.begin()+i);
                if(evaluate(trial)){edits=anchorize(bestOps);any=changed=true;if(i>int(edits.size()))i=edits.size();}
            }
            if(!any)break;
        }
        if(postMode==4||postMode==5){
            for(int round=0;round<4;round++){
                bool improved=false;
                for(int j=int(edits.size())-1;j>=1&&!improved;j--)for(int i=j-1;i>=0&&!improved;i--){
                    auto trial=edits;trial.erase(trial.begin()+j);trial.erase(trial.begin()+i);
                    if(evaluate(trial)){edits=anchorize(bestOps);changed=improved=true;}
                }
                if(!improved)break;
                for(int i=int(edits.size())-1;i>=0;i--){auto trial=edits;trial.erase(trial.begin()+i);if(evaluate(trial)){edits=anchorize(bestOps);changed=true;if(i>int(edits.size()))i=edits.size();}}
            }
        }
        if(postMode==2||postMode==3||postMode==5){
            // Try structural gap anchors; all later operations keep their paper anchors.
            for(int i=int(edits.size())-1;i>=0;i--){
                if(postMode>=3&&!initialExtra[edits[i].k]){int repeats=0;for(auto&e:edits)repeats+=e.k==edits[i].k;if(repeats<2)continue;}
                auto ord=initial.order;
                for(int t=0;t<i;t++){auto[k,a]=edits[t];ord.erase(std::find(ord.begin(),ord.end(),k));int d=a<0?0:int(std::find(ord.begin(),ord.end(),a)-ord.begin())+1;ord.insert(ord.begin()+d,k);}
                int k=edits[i].k;std::vector<int> anchors{-1};
                auto add=[&](int a){if(a!=k&&std::find(anchors.begin(),anchors.end(),a)==anchors.end())anchors.push_back(a);};
                int last=-1;std::array<bool,64>seen{};
                for(int x:ord)if(x!=k){
                    if(col[k]<0){if(col[x]<0){add(last);add(x);}}
                    else{
                        if(col[x]>=0&&!seen[col[x]]){seen[col[x]]=true;if(col[x]<=col[k])add(last);}
                        if(col[x]==col[k]){add(last);add(x);}
                        if(col[x]<0)add(x);
                    }
                    last=x;
                }
                for(int t=i+1;t<int(edits.size());t++)if(edits[t].k==k)add(edits[t].anchor);
                auto chosen=edits;
                for(int a:anchors){if(a==edits[i].anchor)continue;auto trial=edits;trial[i].anchor=a;if(evaluate(trial)){chosen=anchorize(bestOps);changed=true;}}
                edits=std::move(chosen);
                if(i>=int(edits.size()))i=edits.size()-1;
            }
            for(int i=int(edits.size())-1;i>=0;i--){auto trial=edits;trial.erase(trial.begin()+i);if(evaluate(trial)){edits=anchorize(bestOps);changed=true;if(i>int(edits.size()))i=edits.size();}}
        }
        if(changed)postChanged++;
        postSaved+=int(ops.size())-int(bestOps.size());
        restore(bestState);return bestOps;
    }

    // Joint selection of old main, old patches, and newly extracted patches.
    // An interval [level, home] is reserved by each chosen patch; the DP
    // chooses their combination before any old sheet is returned home.
    void joint_plan(int u,double relevelCharge=0.5,double stayCharge=0.8){
        int d=ded[u],oldMain=main,dc=col[d];
        if(d==oldMain){invalid=true;return;}
        U64 wanted=~paper[d].opaque&~low(G);
        auto originalBad=outliers();bool dOut=originalBad[d];
        std::vector<int> old,oldLevel(192,-2);
        int level=H;
        for(int i=191;i>=0;i--){
            int k=order[i];if(col[k]<0)continue;
            if(!originalBad[k])level=col[k];else oldLevel[k]=level;
        }
        for(int k:order)if(originalBad[k]&&k!=d&&k!=oldMain)old.push_back(k);
        std::vector<std::vector<int>> qs(H);
        for(int k:order)if(col[k]>=0&&!originalBad[k])qs[col[k]].push_back(k);
        std::vector<int> fixCost(H);
        for(int c=0;c<H;c++)if(wanted>>handle[c]&1){
            for(int k:qs[c]){if(int(paper[k].black>>handle[c]&1)==int(A[u]>>handle[c]&1))break;fixCost[c]++;}
        }
        auto last_wrong=[&](int k){
            int l=0;U64 wrong=paper[k].opaque&wanted&(paper[k].black^A[u]);
            for(int j=0;j<=col[k];j++)if(wrong>>handle[j]&1)l=j+1;
            return l;
        };
        auto saved=[&](int k,int l,bool skipOwn){
            int sum=0,c=col[k];
            for(int j=l;j<=c;j++)if((paper[k].opaque&wanted)>>handle[j]&1)if(!skipOwn||j!=c)sum+=fixCost[j];
            return sum;
        };
        auto generic_harm=[&](int k){
            int firstGeneric=192;for(int i=0;i<192;i++)if(col[order[i]]<0){firstGeneric=i;break;}
            return pos(k)<firstGeneric&&(paper[k].opaque&low(G)&~paper[d].opaque&(paper[k].black^A[u]));
        };
        struct JC{int k=-1,l=0,c=0,depth=0,kind=0;bool post=false;double gain=0;};
        std::vector<std::vector<JC>> candidates(H);
        auto add_old=[&](int k,bool wasMain){
            int c=col[k],l=last_wrong(k),original=oldLevel[k];
            if(generic_harm(k))original=-2;
            if(!dOut&&c>=dc&&(paper[k].opaque>>handle[dc]&1))l=std::max(l,dc+1);
            for(int a=l;a<=c;a++){
                if(a>l&&!((paper[k].opaque&wanted)>>handle[a]&1)&&a!=original)continue;
                double gain=saved(k,a,false)-relevelCharge;
                int kind=wasMain?3:1;
                if(!wasMain&&a==original){gain=saved(k,a,false)+1-stayCharge;kind=2;}
                if(gain>0)candidates[c].push_back({k,a,c,0,kind,false,gain});
            }
        };
        for(int k:old)add_old(k,false);
        if(oldMain>=0)add_old(oldMain,true);
        for(int c=0;c<H;c++){
            bool ownHole=wanted>>handle[c]&1;
            if(c==dc||(dOut&&!ownHole))continue;
            for(int dep=0;dep<int(qs[c].size())&&dep<=3;dep++){
                int k=qs[c][dep];if(k==d)continue;int l=last_wrong(k);
                for(int a=l;a<=c;a++){
                    if(a>l&&!((paper[k].opaque&wanted)>>handle[a]&1))continue;
                    bool post=dOut||(c>dc&&a<=dc&&(paper[k].opaque>>handle[dc]&1));
                    if(post&&!ownHole)continue;
                    double gain=saved(k,a,dep==0&&ownHole)-1-dep;
                    if(gain>=1)candidates[c].push_back({k,a,c,dep,0,post,gain});
                }
            }
        }
        std::vector<double> best(H+1);std::vector<int> choice(H+1,-1);
        for(int c=0;c<H;c++){
            best[c+1]=best[c];
            for(int i=0;i<int(candidates[c].size());i++){
                const auto&p=candidates[c][i];
                if(best[p.l]+p.gain>best[c+1]+1e-9){best[c+1]=best[p.l]+p.gain;choice[c+1]=i;}
            }
        }
        std::vector<JC> picks;
        for(int j=H;j>0;){if(choice[j]<0){j--;continue;}picks.push_back(candidates[j-1][choice[j]]);j=picks.back().l;}
        std::vector<int> decision(192,0),newLevel(192,-1);
        for(auto&p:picks)if(p.kind){decision[p.k]=p.kind;newLevel[p.k]=p.l;}
        auto move_level=[&](int k,int l,bool lazy,bool belowGeneric){
            auto bad=outliers();int q=192,last=-1;
            for(int i=0;i<192;i++){
                int x=order[i];
                if(col[x]<0){if(belowGeneric)last=i;continue;}
                if(x==k||bad[x])continue;
                if(col[x]<l)last=i;else if(q==192)q=i;
            }
            int from=pos(k);if(lazy&&from<q&&from>last)return;
            move(k,q-(from<q));
        };
        std::vector<char> returned(192);
        // Some old patches are hidden by the old main. Return the visible
        // unselected ones first, then deal with the old main, then the rest.
        for(int i=int(old.size())-1;i>=0;i--){int k=old[i];if(!decision[k]&&visible(k)){insert_home(k,u);returned[k]=1;if(invalid)return;}}
        if(oldMain>=0){
            if(decision[oldMain]){
                bool harm=generic_harm(oldMain);main=-1;
                move_level(oldMain,newLevel[oldMain],true,harm);if(invalid)return;
            }else{insert_home(oldMain,u);if(invalid)return;}
        }
        for(int remaining=int(old.size()),pass=0;remaining&&pass<192;pass++){
            remaining=0;bool progress=false;
            for(int i=int(old.size())-1;i>=0;i--){int k=old[i];if(decision[k]||returned[k])continue;remaining++;
                if(visible(k)){insert_home(k,u);returned[k]=1;progress=true;if(invalid)return;}
            }
            if(remaining&&!progress){invalid=true;return;}
        }
        for(int k:old)if(decision[k]==1){bool harm=generic_harm(k);move_level(k,newLevel[k],true,harm);if(invalid)return;}
        set_generic(u);if(invalid)return;
        auto place=[&](const JC&p){expose(p.k,u);if(invalid)return;move_level(p.k,p.l,false,false);};
        for(auto&p:picks)if(p.kind==0&&!p.post){place(p);if(invalid)return;}
        if(!dOut){expose(d,u);if(invalid)return;}
        move(d,0);main=d;if(invalid)return;
        for(auto&p:picks)if(p.kind==0&&p.post){place(p);if(invalid)return;}
        fix(u);if(invalid)return;
        // Every retained patch must become visible when the main is removed.
        // This guarantees that the next request can return it legally.
        auto finalBad=outliers(false);
        for(int k:order)if(finalBad[k]){
            U64 covered=0;bool ok=false;
            for(int x:order){if(x==main)continue;if(x==k){ok=(paper[k].opaque&~covered)!=0;break;}covered|=paper[x].opaque;}
            if(!ok){invalid=true;return;}
        }
    }
    std::vector<std::pair<int,int>> process_fast(int u){
        moves.clear();invalid=false;
        if(display()==A[u])return moves;
        cleanup(u);set_generic(u);int d=ded[u];expose(d,u);move(d,0);main=d;fix(u);
        if(invalid||moves.size()>384||display()!=A[u]){std::cerr<<"fast fallback failed\n";std::exit(4);}
        return moves;
    }
    std::vector<std::pair<int,int>> process(int u){
        if(display()==A[u])return {};
        int d=ded[u];State original=state();
        std::vector<std::pair<int,int>> bestMoves;State bestState;double bestCost=1e100;
        auto consider=[&](){
            if(invalid||moves.size()>384||display()!=A[u])return;

            auto bad=outliers(false);int count=std::count(bad.begin(),bad.end(),1);
            double score=moves.size()+patchPenalty*count+futureWeight*future();
            if(score<bestCost){bestCost=score;bestMoves=moves;bestState=state();}
        };
        for(int reuse=0;reuse<4;reuse++){
            restore(original);cleanup_reuse(u,reuse);if(invalid)continue;set_generic(u);if(invalid)continue;expose(d,u);if(invalid)continue;
            State prepared=state();auto prefix=moves;
            move(d,0);main=d;fix(u);consider();
            restore(prepared);moves=prefix;greedy_patches(u,d,2);consider();
        }
        restore(original);joint_plan(u);double beforeJoint=bestCost;consider();if(bestCost<beforeJoint)jointUsed++;

        if(bestCost>1e90){std::cerr<<"no valid plan\n";std::exit(3);}
        restore(bestState);return post_optimize(original,bestMoves,u);
    }
};
int fallback(const std::vector<U64>&A,int R){
    for(int k=0;k<192;k++){std::string s(64,'.');if(k<128)s[k%64]=k<64?'0':'1';std::cout<<s<<'\n';}std::cout<<std::flush;
    U64 current=0;long long total=0;
    for(int r=0;r<R;r++){int u;if(!(std::cin>>u)||u<0)return 0;U64 diff=A[u]^current;std::cout<<pc(diff)<<'\n';
        for(U64 z=diff;z;z&=z-1){int j=__builtin_ctzll(z);std::cout<<j+((current>>j&1)?64:0)<<" 191\n";total++;}
        current=A[u];std::cout<<std::flush;}
    std::cerr<<"fallback = 1\nmoves = "<<total<<'\n';return 0;
}
int main(int argc,char**argv){
    std::ios::sync_with_stdio(false);std::cin.tie(nullptr);
    int N,K,P,R;if(!(std::cin>>N>>K>>P>>R))return 0;
    std::vector<U64>A(P);for(auto&a:A){std::string s;std::cin>>s;for(int j=0;j<N;j++)if(s[j]=='1')a|=1ULL<<j;}
    if(N!=64||K!=192||P!=256)return 0;auto original=A;
#ifdef BARCODE_FORCE_BITS
    return fallback(original,R);
#endif
    int M=argc>1?std::atoi(argv[1]):6,G=argc>2?std::atoi(argv[2]):36;
    double budget=argc>5?std::atof(argv[5]):1.65;
    auto start=std::chrono::steady_clock::now();auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
    Comparator comp;Random rng;std::unique_ptr<PaperDesign> des;std::vector<int> permutation(64);
    for(int attempt=0;attempt<3;attempt++){
        if(elapsed()>0.80)return fallback(original,R);
        A=original;std::iota(permutation.begin(),permutation.end(),0);comp.init(M,G,rng);
        optimize_map(A,comp,permutation,attempt==0?0.25:0.10);
        des=std::make_unique<PaperDesign>(A,M,G);if(des->initialize(comp,[&](){return elapsed()>0.90;}))break;
        des.reset();G-=4;
    }
    if(!des)return fallback(original,R);
    des->anneal(std::max(0.01,(argc>6?std::atof(argv[6]):1.10)-elapsed()));
    auto beforePermutation=permutation;
    for(int c=0;c<64-G;c++)permutation[G+c]=beforePermutation[des->handle[c]];
    for(auto&a:A){U64 b=a&low(G);for(int c=0;c<64-G;c++)b|=(a>>des->handle[c]&1)<<(G+c);a=b;}
    Solver s;s.M=M;s.G=G;s.H=64-G;s.comp=comp;s.A=A;s.handle.resize(s.H);std::iota(s.handle.begin(),s.handle.end(),G);
    if(argc>7)s.topPenalty=std::atof(argv[7]);
    if(argc>8)s.futureWeight=std::atof(argv[8]);
    if(argc>9)s.patchPenalty=std::atof(argv[9]);
    if(argc>10)s.postMode=std::atoi(argv[10]);
    s.paper.resize(K);s.col.assign(K,-1);s.ded.assign(P,-1);s.weight.assign(K,0);s.holes.assign(s.H,{0,0});
    for(int i=0;i<M;i++)s.paper[i]={comp.opq[i],comp.black[i]};
    int next=M;U64 mask=low(G);
    for(int c=0;c<s.H;c++){
        mask|=1ULL<<s.handle[c];std::array<std::vector<int>,2> members;
        for(int x=0;x<des->U;x++)if(des->unit[x].c==c)members[des->color(des->unit[x],c)].push_back(x);
        for(auto&v:members)std::stable_sort(v.begin(),v.end(),[&](int a,int b){return des->weight(des->unit[a])<des->weight(des->unit[b]);});
        while(!members[0].empty()||!members[1].empty()){
            int v=members[1].size()>members[0].size();int x=members[v].back();members[v].pop_back();auto&u=des->unit[x];
            U64 opq=mask;if(u.b>=0)opq&=~(A[u.a]^A[u.b]);s.paper[next]={opq,A[u.a]&opq};s.col[next]=c;
            s.ded[u.a]=next;if(u.b>=0)s.ded[u.b]=next;s.weight[next]=des->weight(u);next++;
        }
    }
    if(next!=192||std::find(s.ded.begin(),s.ded.end(),-1)!=s.ded.end())return fallback(original,R);
    for(int c=0;c<s.H;c++){
        int colors=0;for(int k=M;k<K;k++)if(s.col[k]==c)colors|=1<<int(s.paper[k].black>>s.handle[c]&1);
        if(colors!=3)return fallback(original,R);
    }
    for(int u=0;u<256;u++)for(int c=0;c<s.H;c++)if(!(s.paper[s.ded[u]].opaque>>s.handle[c]&1))s.holes[c][A[u]>>s.handle[c]&1]+=1/256.0;
    s.order.resize(K);std::iota(s.order.begin(),s.order.end(),0);
    for(auto&p:s.paper){std::string row(64,'.');for(int j=0;j<64;j++)row[permutation[j]]=!(p.opaque>>j&1)?'.':(p.black>>j&1)?'1':'0';std::cout<<row<<'\n';}std::cout<<std::flush;
    long long total=0,fast=0,quick=0;double designTime=elapsed(),designCPU=double(std::clock())/CLOCKS_PER_SEC;
    bool heavy=true;int fullPostMode=s.postMode;
    for(int r=0;r<R;r++){
        int u;if(!(std::cin>>u)||u<0)return 0;
        double cpu=double(std::clock())/CLOCKS_PER_SEC;
        double reserve=(R-r)*std::max(0.00012,r?0.60*(cpu-designCPU)/r:0.00030);
        if(cpu+reserve>budget)heavy=false;
        s.postMode=heavy?fullPostMode:std::min(1,fullPostMode);
        if(!heavy)fast++;
        std::vector<std::pair<int,int>> ops;
#ifdef BARCODE_FORCE_SIMPLE
        ops=s.process_fast(u);quick++;
#else
        if(cpu>budget+0.10){ops=s.process_fast(u);quick++;}
        else ops=s.process(u);
#endif
        total+=ops.size();std::cout<<ops.size()<<'\n';for(auto[k,d]:ops)std::cout<<k<<' '<<d<<'\n';std::cout<<std::flush;
    }
    std::cerr<<"moves = "<<total<<"\nmean = "<<double(total)/R<<"\ndesign = "<<designTime<<"\nelapsed = "<<elapsed()<<"\ncpu = "<<double(std::clock())/CLOCKS_PER_SEC<<"\nfast = "<<fast<<"\njoint = "<<s.jointUsed<<"\npost_saved = "<<s.postSaved<<"\npost_changed = "<<s.postChanged<<"\nquick = "<<quick<<"\nM = "<<M<<"\nG = "<<G<<"\n";
}
