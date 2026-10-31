
// Begin design2_tour_global_learn.hpp

// Begin design2_tour_order_core.hpp

// Begin design2_tour_order_hub.hpp
#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
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
#if defined(__GNUC__) && (defined(__i386__) || defined(__x86_64__))
#pragma GCC target("popcnt")
#endif

static std::clock_t solverCpuStart;
static double solverCpuLimit=1.80,solverSearchDeadline=1.76,solverTrainDeadline=1.17;
static std::array<int,64> logicalToOriginal;
static uint64_t invertOriginal=0;
static long long teacherFallbackQueries=0;
static double solverCpu(){return double(std::clock()-solverCpuStart)/CLOCKS_PER_SEC;}
static uint64_t seedMix(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}

using namespace std;using U=uint64_t;int pc(U x){return __builtin_popcountll(x);} 
struct Paper{U m=0,v=0;};array<Paper,192>S;vector<U>A;mt19937_64 rng; array<int,64>base,gsz; array<int,192>anchor,slotof; array<int,192>importance{}; bool FREQ=false; int layout=0; int HEAVY_START=40;int PAL=6,NPAT=0;vector<U>BV;int SINGLE=16;int BLOCK=4; double MUST_WEIGHT=4;double POWER=1.4; U MUST=0; vector<U>needmask;array<array<signed char,64>,256>trainChoice;array<array<unsigned char,64>,256>trainCut;
void setup(int mode){SINGLE=mode;MUST=SINGLE?((U(1)<<SINGLE)-1):0;int k=0,extra=192-PAL-1-2*(64-SINGLE);for(int j=0;j<64;j++){gsz[j]=j<SINGLE?(j<=PAL?1:0):2;if(j>=HEAVY_START)gsz[j]+=extra/(64-HEAVY_START)+(j-HEAVY_START<extra%(64-HEAVY_START));base[j]=k;for(int v=0;v<gsz[j];v++){anchor[k]=j;slotof[k]=v;if(j<SINGLE)S[k]={MUST,0};k++;}}assert(k==192);}
U low(int j){return j==63?~U(0):((U(1)<<(j+1))-1);}
int trainClose(U&u,U t,int cut){while(cut<SINGLE){U m=((U(1)<<BLOCK)-1)<<cut;if(u&m&t)break;u&=~m;cut+=BLOCK;}return cut;}
void learn(int starts,int probes,double penalty){
 vector<U>rem(256,~U(0));vector<int>uses(256),cut(256);double totalgain=0;for(auto&x:trainChoice)x.fill(-1);for(int t=0;t<256;t++)cut[t]=trainClose(rem[t],A[t],0);
 for(int j=63;j>=SINGLE;j--){
  int bj=j;double bsc=1e100;
  for(int b=SINGLE;b<=j;b++){double sc=0;for(int t=0;t<256;t++)if(rem[t]>>b&1)sc+=1.; if(sc<bsc){bsc=sc;bj=b;}}
  if(bj!=j){auto sw=[&](U x){if(((x>>bj)^(x>>j))&1)x^=(U(1)<<bj)|(U(1)<<j);return x;};for(auto&x:A)x=sw(x);for(auto&x:rem)x=sw(x);for(auto&p:S){p.m=sw(p.m);p.v=sw(p.v);}swap(logicalToOriginal[bj],logicalToOriginal[j]);}
  U prefix=low(j),an=U(1)<<j;double power=1+(POWER-1)*min(1.,max(0.,(j-SINGLE-3)/double(max(1,64-SINGLE-4))));double weight=MUST_WEIGHT*max(0.,1-(j-SINGLE)/8.);double pen=penalty*min(1.,(j-SINGLE+1)/8.);array<array<double,65>,65>gt;for(int c=0;c<=64;c++)for(int d=0;d<=64;d++)gt[c][d]=pow(c+weight*d,power)-pow(pen,power);auto gain=[&](U m,int t){return gt[pc(m&rem[t])][pc(m&rem[t]&A[t]&MUST)];};vector<double>bestgain(256,0);vector<int>choice(256,-1);
  for(int slot=0;slot<gsz[j];slot++){
   double best=-1;Paper bp{an,slot==1?an:0};
   auto eval=[&](U m,U v){double sum=0;for(int t=0;t<256;t++)if(!((A[t]^v)&m&rem[t]))sum+=max(0.,gain(m,t)-bestgain[t]);return sum;};
   auto update=[&](U m,U v){double z=eval(m,v);if(z>best){best=z;bp={m,v};}return z;};
   for(int st=0;st<starts;st++){
    int t=rng()%256;int color=slot<2?slot:((A[t]>>j)&1);
    if((rem[t]&an)&&int((A[t]>>j)&1)!=color)continue;
    U ones=A[t]&rem[t]&prefix,zeros=~A[t]&rem[t]&prefix,fill=A[t];
    auto pat=[&](U oo,U zz,bool dense){U m=(dense?(prefix&~(oo&zz)):(oo^zz))|an;U v=(oo&~zz)|(fill&~(oo|zz));v=(v&~an)|(color?an:0);return Paper{m,v&m};};
    for(int step=0;step<9;step++){
     auto p=pat(ones,zeros,true);double cur=update(p.m,p.v);p=pat(ones,zeros,false);cur=max(cur,update(p.m,p.v));
     double nxt=-1;U no=ones,nz=zeros;
     for(int z=0;z<probes;z++){
      int tt=rng()%256;if((rem[tt]&an)&&int((A[tt]>>j)&1)!=color)continue;
      U oo=ones|(A[tt]&rem[tt]&prefix),zz=zeros|(~A[tt]&rem[tt]&prefix);auto pp=pat(oo,zz,true);double f=update(pp.m,pp.v);auto pp2=pat(oo,zz,false);f=max(f,update(pp2.m,pp2.v));
      if(f>nxt){nxt=f;no=oo;nz=zz;}
     }
     if(nxt<0)break;
     if(nxt<cur && step>2 && rng()%4)break;
     if(no==ones&&nz==zeros)break;ones=no;zeros=nz;
    }
   }
   S[base[j]+slot]=bp;
   for(int t=0;t<256;t++)if(!((A[t]^bp.v)&bp.m&rem[t])){double g=gain(bp.m,t);if(g>bestgain[t]){bestgain[t]=g;choice[t]=slot;}}
  }
  for(int t=0;t<256;t++)if(choice[t]>=0){trainChoice[t][j]=choice[t];trainCut[t][j]=cut[t];importance[base[j]+choice[t]]++;rem[t]&=~S[base[j]+choice[t]].m;cut[t]=trainClose(rem[t],A[t],cut[t]);uses[t]++;totalgain+=bestgain[t];}
 }
 double m=accumulate(uses.begin(),uses.end(),0.)/256,r=0;for(auto x:rem)r+=pc(x)/256.;cerr<<"learn m "<<m<<" r "<<r<<" modeled "<<(penalty*m+r)/2<<" gain "<<totalgain/512<<"\n";
 int badTargets=0,badBits=0;for(int t=0;t<256;t++){int b=pc(rem[t]&A[t]&MUST);badTargets+=b>0;badBits+=b;}cerr<<"mandatory greedy remaining targets "<<badTargets<<" bits "<<badBits<<"\n"; cerr<<"residual per 8bits ";for(int b=0;b<8;b++){double z=0;for(auto x:rem)z+=pc((x>>(8*b))&255)/256.;cerr<<z<<" ";}cerr<<"\n";
}
bool INTERVAL=false, BRIDGE=false;
struct Plan{U u,sel0,sel1,sel2,sel3;int cost;double key;array<unsigned char,64>cut{};array<unsigned char,64>seq{};};
Plan LAST_PLAN;array<Plan,256>fallback;bool USE_FALLBACK=false;unordered_map<U,int>targetId; const int INF=100000;
struct Hub{
 array<vector<int>,64> group;vector<int>old;
 array<int,192>ord;long long moves=0;bool check=true;bool record=false;vector<pair<int,int>>operations;
 Hub(){iota(ord.begin(),ord.end(),0);for(int j=0;j<64;j++){for(int v=0;v<gsz[j];v++)group[j].push_back(base[j]+v);}}
 U display(){U cov=0,v=0;for(int p:ord){v|=S[p].v&~cov;cov|=S[p].m;}return v;}
 void mv(int k,int d){int pos=find(ord.begin(),ord.end(),k)-ord.begin();if(check){U cov=0;for(int i=0;i<pos;i++)cov|=S[ord[i]].m;if(!(S[k].m&~cov)){cerr<<"ILLEGAL "<<k<<" d "<<d<<"\n";abort();}}if(pos<d)move(ord.begin()+pos+1,ord.begin()+d+1,ord.begin()+pos);else if(pos>d)move_backward(ord.begin()+d,ord.begin()+pos,ord.begin()+pos+1);ord[d]=k;moves++;if(record)operations.push_back({k,d});}
 void before(int k,int ref){int p=find(ord.begin(),ord.end(),k)-ord.begin(),r=find(ord.begin(),ord.end(),ref)-ord.begin();mv(k,r-(p<r));}
 void after(int k,int ref){int p=find(ord.begin(),ord.end(),k)-ord.begin(),r=find(ord.begin(),ord.end(),ref)-ord.begin();mv(k,r+1-(p<r));}
 int color(int p){return (S[p].v>>anchor[p])&1;}
 int insert_pos(vector<int>const&g,int p,int x){int at=find(g.begin(),g.end(),p)-g.begin()+1;bool opp=at<(int)g.size()&&color(g[at])!=color(p);if(color(x)!=color(p)&&(!opp||importance[x]>importance[g[at]]))return at;if(opp)at++;while(at<(int)g.size()&&importance[g[at]]>=importance[x])at++;return at;}
 void expose(int j,int p){if(gsz[j]==1){assert(group[j][0]==p);return;}auto&g=group[j];while(g[0]!=p){int x=g[0];g.erase(g.begin());int ix=find(g.begin(),g.end(),p)-g.begin();int at=FREQ?insert_pos(g,p,x):(color(x)!=color(p)?ix+1:g.size());after(x,g[at-1]);g.insert(g.begin()+at,x);}if(color(g[0])==color(g[1])){cerr<<"head invariant fail j "<<j<<" p "<<p<<"\n";abort();}}
 int run(U target,int bw,double beta){
  long long initial=moves;array<int,64>prev;prev.fill(-1);for(int p:old)prev[anchor[p]]=p;
  array<int,64>flip{};array<array<int,20>,64>access;U wrong=target&MUST;for(int j=0;j<SINGLE;j++){flip[j]=(target>>j&1)?INF:0;access[j][0]=0;}
  for(int j=SINGLE;j<64;j++){
   auto&g=group[j];if(prev[j]>=0){flip[j]=0;int p=prev[j];access[j][slotof[p]]=0;for(int ix=0;ix<(int)g.size();ix++)access[j][slotof[g[ix]]]=ix;}
   else{flip[j]=(color(g[0])!=int(target>>j&1))?(gsz[j]==1?INF:1):0;for(int ix=0;ix<gsz[j];ix++)access[j][slotof[g[ix]]]=ix;if(flip[j])wrong|=U(1)<<j;}
  }
  Plan plan;
  if(INTERVAL){
   array<vector<Plan>,65>buckets;int bestcost=(wrong&MUST)?INF:pc(wrong);plan={0,0,0,0,0,bestcost,0};
   if(USE_FALLBACK){plan=fallback[targetId[target]];U cov=0;int cost=0;for(int j=0;j<64;j++){int code=((plan.sel0>>j)&1)+2*((plan.sel1>>j)&1)+4*((plan.sel2>>j)&1)+8*((plan.sel3>>j)&1);if(code){cov|=S[base[j]+code-1].m&~(plan.cut[j]?low(plan.cut[j]-1):0);cost+=2+access[j][code-1];}}for(int j=0;j<64;j++)if(!(cov>>j&1))cost+=flip[j];plan.cost=bestcost=cost;}

   auto normalize=[&](Plan&n){U ww=n.u&wrong;if(!ww){n.u=0;return 64;}int at=__builtin_ctzll(ww),cut=at<SINGLE?at/BLOCK*BLOCK:at;if(cut)n.u&=~low(cut-1);return at;};
   Plan init{~U(0),0,0,0,0,0,0};int ii=normalize(init);buckets[ii].push_back(init);
   for(int i=0;i<64;i++){
    auto&bucket=buckets[i];sort(bucket.begin(),bucket.end(),[](auto&a,auto&b){return a.key<b.key;});vector<Plan>beam;unordered_set<U>seen;
    for(auto&n:bucket){U used=n.sel0|n.sel1|n.sel2|n.sel3;U h=n.u^(used*0x9e3779b97f4a7c15ULL);if(seen.insert(h).second){beam.push_back(n);if((int)beam.size()==bw)break;}}vector<Plan>().swap(bucket);
    auto add=[&](Plan n){if(n.cost>=bestcost)return;int ni=normalize(n);if(ni==64){bestcost=n.cost;plan=n;return;}n.key=n.cost+beta*pc(n.u&wrong);buckets[ni].push_back(n);if(buckets[ni].size()>size_t(bw*16)){auto&v=buckets[ni];nth_element(v.begin(),v.begin()+bw*4,v.end(),[](auto&a,auto&b){return a.key<b.key;});v.resize(bw*4);}};
    for(auto n:beam){Plan nn=n;nn.cost+=flip[i];nn.u&=~(U(1)<<i);add(nn);U used=n.sel0|n.sel1|n.sel2|n.sel3;
     for(int a=i+1;a<64;a++)if(!(used>>a&1))for(int v=0;v<gsz[a];v++){int p=base[a]+v;if(!(S[p].m>>i&1)||((S[p].v^target)&S[p].m&n.u))continue;nn=n;nn.u&=~S[p].m;nn.cost+=2+access[a][v];int code=v+1;if(code&1)nn.sel0|=U(1)<<a;if(code&2)nn.sel1|=U(1)<<a;if(code&4)nn.sel2|=U(1)<<a;if(code&8)nn.sel3|=U(1)<<a;nn.cut[a]=i<SINGLE?i/BLOCK*BLOCK:i;nn.seq[a]=pc(used);add(nn);}
     if(BRIDGE && n.cost+4<bestcost){
      vector<int>good,badmain;for(int a=i+1;a<64;a++)if(!(used>>a&1))for(int v=0;v<gsz[a];v++){int p=base[a]+v;U bad=(S[p].v^target)&S[p].m&n.u;if(S[p].m>>i&1){if(bad)badmain.push_back(p);}else if(!bad&&(S[p].m&n.u)&&n.cost+4+access[a][v]<bestcost)good.push_back(p);}
      for(int q:good){int a=anchor[q],v=slotof[q];int cq=2+access[a][v];U uq=n.u&~S[q].m;
       for(int p:badmain){int b=anchor[p],w=slotof[p];if(a==b||((S[p].v^target)&S[p].m&uq))continue;int cp=2+access[b][w];if(n.cost+cq+cp>=bestcost)continue;Plan z=n;z.u=uq&~S[p].m;z.cost+=cq+cp;
        int c=v+1;if(c&1)z.sel0|=U(1)<<a;if(c&2)z.sel1|=U(1)<<a;if(c&4)z.sel2|=U(1)<<a;if(c&8)z.sel3|=U(1)<<a;z.cut[a]=i<SINGLE?i/BLOCK*BLOCK:i;z.seq[a]=pc(used);
        c=w+1;if(c&1)z.sel0|=U(1)<<b;if(c&2)z.sel1|=U(1)<<b;if(c&4)z.sel2|=U(1)<<b;if(c&8)z.sel3|=U(1)<<b;z.cut[b]=i<SINGLE?i/BLOCK*BLOCK:i;z.seq[b]=pc(used)+1;add(z);
       }
      }
     }
    }
   }
  }else{
  vector<Plan>beam{{~U(0),0,0,0,0,0,0}};
  for(int j=63;j>=0;j--){vector<Plan>cand;cand.reserve(beam.size()*(gsz[j]+1));U bit=U(1)<<j;
   for(auto n:beam){for(int v=-1;v<(j<SINGLE?0:gsz[j]);v++){
     Plan nn=n;if(v>=0){auto&p=S[base[j]+v];if((p.v^target)&p.m&n.u)continue;nn.u&=~p.m;nn.cost+=2+access[j][v];int code=v+1;if(code&1)nn.sel0|=bit;if(code&2)nn.sel1|=bit;if(code&4)nn.sel2|=bit;if(code&8)nn.sel3|=bit;}
     if(nn.u&bit)nn.cost+=flip[j];if(nn.cost>=INF)continue;nn.u&=~bit;nn.key=nn.cost+beta*pc(nn.u&wrong);cand.push_back(nn);
   }}
   sort(cand.begin(),cand.end(),[](auto&a,auto&b){return a.key<b.key;});beam.clear();unordered_set<U>seen;seen.reserve(bw*2+1);for(auto&n:cand)if(seen.insert(n.u).second){beam.push_back(n);if((int)beam.size()==bw)break;}
  }
  if(beam.empty()){plan.cost=INF;}else plan=*min_element(beam.begin(),beam.end(),[](auto&a,auto&b){return a.cost<b.cost;});
  }
  LAST_PLAN=plan;if(plan.cost>=INF)return -1; array<int,64>pick;pick.fill(-1);U covered=0;for(int j=0;j<64;j++){int c=((plan.sel0>>j)&1)+2*((plan.sel1>>j)&1)+4*((plan.sel2>>j)&1)+8*((plan.sel3>>j)&1);if(c){pick[j]=base[j]+c-1;U mm=S[pick[j]].m;if(INTERVAL&&plan.cut[j])mm&=~low(plan.cut[j]-1);covered|=mm;}}
  // Undo old promotions, each is currently the topmost remaining promoted card.
  for(auto it=old.rbegin();it!=old.rend();++it){int p=*it,j=anchor[p];auto&g=group[j];if(j<SINGLE){int r=j+1;while(r<64&&group[r].empty())r++;before(p,group[r][0]);g.push_back(p);continue;}int q=g[0],r=g[1];int desired=pick[j];
   if(desired<0)desired=color(p)==int(target>>j&1)?p:q;
   if(desired==p){before(p,q);g.insert(g.begin(),p);}
   else{int at=FREQ?insert_pos(g,desired,p):int(find(g.begin(),g.end(),desired)-g.begin()+1);after(p,g[at-1]);g.insert(g.begin()+at,p);}
  }

  old.clear();
  // All local rotations happen in the hub before any promotion.
  for(int j=SINGLE;j<64;j++){
   if(pick[j]>=0)expose(j,pick[j]);
   else if(!(covered>>j&1)){int desired=group[j][0];if(color(desired)!=int(target>>j&1)){for(int q:group[j])if(color(q)==int(target>>j&1)){desired=q;break;}}expose(j,desired);}
   else if(gsz[j]>1&&color(group[j][0])==color(group[j][1])){cerr<<"unused bad heads\n";abort();}
  }
  for(int j=0;j<64;j++)if(pick[j]>=0){int p=pick[j];if(INTERVAL){int c=plan.cut[j];while(c<64&&group[c].empty())c++;int ref=group[c][0],sr=100;for(int a=0;a<j;a++)if(pick[a]>=0&&plan.cut[a]==plan.cut[j]&&plan.seq[a]>plan.seq[j]&&plan.seq[a]<sr){sr=plan.seq[a];ref=pick[a];}before(p,ref);}else mv(p,0);group[j].erase(group[j].begin());old.push_back(p);}
  if(display()!=target){cerr<<"WRONG display "<<pc(display()^target)<<"\n";abort();}
  int actual=moves-initial;int amort=actual-(int)prevcount(prev)+(int)old.size();
  if(amort!=plan.cost){cerr<<"COST mismatch "<<amort<<" predicted "<<plan.cost<<" actual "<<actual<<"\n";abort();}
  return actual;
 }
 int prevcount(array<int,64>const&prev){int n=0;for(int p:prev)n+=p>=0;return n;}
};

// End design2_tour_order_hub.hpp

array<int,64> edgeA{},edgeB{};int EDGE_COUNT=0;U EDGE_MASK=0;
using NativeOrder=array<unsigned char,8>;
array<NativeOrder,256> trainedNative;
U nativeWord(NativeOrder const&o){array<int,8>rank{};for(int i=0;i<PAL;i++)rank[o[i]]=i;U w=0;for(int e=0;e<EDGE_COUNT;e++)if(rank[edgeB[e]]<rank[edgeA[e]])w|=1ULL<<e;return w;}
array<unsigned char,8> targetGraph(U u,U target,NativeOrder const&current){
 array<int,8>rank{};for(int i=0;i<PAL;i++)rank[current[i]]=i;array<unsigned char,8>adj{};
 U bits=u&EDGE_MASK;while(bits){int e=__builtin_ctzll(bits);bits&=bits-1;int a=rank[edgeA[e]],b=rank[edgeB[e]];if(target>>e&1)swap(a,b);adj[a]|=1u<<b;}return adj;
}
int feedbackCost(array<unsigned char,8>const&adj){
 array<unsigned char,256>dp;dp.fill(100);dp[0]=0;int all=(1<<PAL)-1;
 for(int m=1;m<=all;m++){int q=m;while(q){int v=__builtin_ctz(q);q&=q-1;int rest=m^(1<<v);dp[m]=min<int>(dp[m],dp[rest]+pc(adj[v]&rest));}}return dp[all];
}
U nearestPaletteMask(U u,U target){
 NativeOrder identity{};for(int i=0;i<PAL;i++)identity[i]=i;auto adj=targetGraph(u,target,identity);
 array<unsigned char,256>dp,choice;dp.fill(100);dp[0]=0;int all=(1<<PAL)-1;
 for(int m=1;m<=all;m++){int q=m;while(q){int v=__builtin_ctz(q);q&=q-1;int rest=m^(1<<v),val=dp[rest]+pc(adj[v]&rest);if(val<dp[m]){dp[m]=val;choice[m]=v;}}}
 NativeOrder order{};int m=all;for(int i=PAL-1;i>=0;i--){int v=choice[m];order[i]=v;m^=1<<v;}
 return u&MUST&(target^nativeWord(order));
}
bool feasibleNative(U u,U target,NativeOrder*result=nullptr){
 if(u&target&MUST&~EDGE_MASK)return false;NativeOrder identity{};for(int i=0;i<PAL;i++)identity[i]=i;auto adj=targetGraph(u,target,identity);
 int remaining=(1<<PAL)-1;NativeOrder order{};
 for(int i=0;i<PAL;i++){int incoming=0;for(int j=0;j<PAL;j++)if(remaining>>j&1)incoming|=adj[j];int ready=remaining&~incoming;if(!ready)return false;int v=__builtin_ctz(ready);order[i]=v;remaining^=1<<v;}
 if(result)*result=order;return true;
}
struct NativeInfo {int mismatch=0,closure=100;NativeOrder order{};};
NativeInfo optimizeNative(U u,U target,NativeOrder const&current){
 auto adj=targetGraph(u,target,current);auto reach=adj;for(int k=0;k<PAL;k++)for(int i=0;i<PAL;i++)if(reach[i]>>k&1)reach[i]|=reach[k];
 NativeInfo out;bool cyclic=false;for(int i=0;i<PAL;i++)cyclic|=(reach[i]>>i)&1;
 out.mismatch=pc(u&target&MUST&~EDGE_MASK);
 if(cyclic||out.mismatch){out.mismatch+=cyclic?feedbackCost(adj):0;return out;}
 int all=(1<<PAL)-1,sinks=0;for(int i=0;i<PAL;i++)if(!adj[i])sinks|=1<<i;
 bool bottomSink=sinks>>(PAL-1)&1;array<unsigned char,256>good{};good[0]=1;int best=-1,bn=-1;
 for(int m=0;m<=all;m++){
  if(m){int j=31-__builtin_clz(m),rest=m^(1<<j);good[m]=good[rest]&&!(reach[j]&rest);}
  if(good[m]&&(bottomSink||(sinks&~m))&&pc(m)>bn){bn=pc(m);best=m;}
 }
 if(best<0)abort();out.closure=PAL-bn;
 int last;if(bottomSink&&(best>>(PAL-1)&1))last=PAL-1;else last=31-__builtin_clz(sinks&~best);
 auto graph=adj;int prev=-1;for(int i=0;i<PAL;i++)if(best>>i&1){if(prev>=0)graph[prev]|=1<<i;prev=i;}
 int remaining=all;
 for(int at=0;at<PAL;at++){
  int incoming=0;for(int i=0;i<PAL;i++)if(remaining>>i&1)incoming|=graph[i];int ready=remaining&~incoming;if(at<PAL-1)ready&=~(1<<last);
  if(!ready){cerr<<"native topo failure"<<endl;abort();}int v=__builtin_ctz(ready);out.order[at]=current[v];remaining^=1<<v;
 }
 return out;
}
void initTournament(){
 for(int k=0;k<PAL;k++)S[k]={0,0};EDGE_COUNT=0;
 for(int a=0;a<PAL;a++)for(int b=a+1;b<PAL;b++){int e=EDGE_COUNT++;if(e>=SINGLE)abort();edgeA[e]=a;edgeB[e]=b;S[a].m|=1ULL<<e;S[b].m|=1ULL<<e;S[b].v|=1ULL<<e;}
 EDGE_MASK=(1ULL<<EDGE_COUNT)-1;S[PAL]={MUST,0};double mean=0;for(auto a:A)mean+=pc(nearestPaletteMask(MUST,a))/256.;cerr<<"TOURNAMENT cards "<<PAL<<" edges "<<EDGE_COUNT<<" nearest "<<mean<<endl;
}

// End design2_tour_order_core.hpp

array<array<int,16>,256>nativeColor;array<array<int,16>,256>guardOrder;array<int,256>guardCount{};array<U,256>closedGuard{};int G=4;bool CLOSURE_BONUS=true;array<U,16>GM{};
int closeAny(U&u,U target,int t){while(guardCount[t]<PAL){int v=-1;for(int k=0;k<PAL;k++)if(!(closedGuard[t]>>k&1)&&!((S[k].v^target)&S[k].m&u)){v=k;break;}if(v<0)break;trainedNative[t][guardCount[t]]=v;guardOrder[t][guardCount[t]++]=v;closedGuard[t]|=1ULL<<v;u&=~S[v].m;}if(guardCount[t]==PAL)u&=~MUST;return guardCount[t];}
vector<int>LEARN_ORDER;array<vector<pair<int,int>>,256>trainSequence;
void learnAny(int starts,int probes,double penalty){
 vector<U>rem(256,~U(0)),used(256);vector<int>uses(256),cut(256);array<bool,64>processed{};array<int,64>made{};
 for(auto&x:trainChoice)x.fill(-1);for(int t=0;t<256;t++)cut[t]=closeAny(rem[t],A[t],t);
 int firstSlots=getenv("FIRST_SLOTS")?atoi(getenv("FIRST_SLOTS")):4,secondSlots=getenv("SECOND_SLOTS")?atoi(getenv("SECOND_SLOTS")):4;
 double totalgain=0;vector<double>bestgain(256);vector<int>bestcard(256,-1);array<U,256>minority{};
 auto reset=[&](){fill(bestgain.begin(),bestgain.end(),0);fill(bestcard.begin(),bestcard.end(),-1);for(int t=0;t<256;t++)minority[t]=nearestPaletteMask(rem[t],A[t]);};
 auto commit=[&](int t){int p=bestcard[t];if(p<0)return;int j=anchor[p],v=slotof[p];used[t]|=1ULL<<j;trainSequence[t].push_back({j,v});trainChoice[t][j]=v;trainCut[t][j]=cut[t];importance[p]++;rem[t]&=~S[p].m;cut[t]=closeAny(rem[t],A[t],t);uses[t]++;totalgain+=bestgain[t];};
 auto gainGlobal=[&](U m,int t){return pow(pc(m&rem[t]),POWER)-pow(penalty,POWER);};
 auto considerGlobal=[&](int p){int j=anchor[p];auto bp=S[p];for(int t=0;t<256;t++)if(!(used[t]>>j&1)&&!((A[t]^bp.v)&bp.m&rem[t])){double g=gainGlobal(bp.m,t);if(g>bestgain[t]){bestgain[t]=g;bestcard[t]=p;}}};
 auto trainGroup=[&](int j,int end,bool global){
  if(!global)reset();
  if(!processed[j]&&!getenv("NO_ADAPT")){
   int lo=SINGLE;for(int k=SINGLE;k<j;k++)if(processed[k])lo=k+1;int bj=j;double bsc=1e100;
   for(int b=lo;b<=j;b++){double sc=0;for(int t=0;t<256;t++)if(rem[t]>>b&1)sc++;if(sc<bsc){bsc=sc;bj=b;}}
   if(bj!=j){auto sw=[&](U x){if(((x>>bj)^(x>>j))&1)x^=(1ULL<<bj)|(1ULL<<j);return x;};for(auto&x:A)x=sw(x);for(auto&x:rem)x=sw(x);for(auto&p:S){p.m=sw(p.m);p.v=sw(p.v);}swap(logicalToOriginal[bj],logicalToOriginal[j]);}
  }
  processed[j]=true;end=min(end,gsz[j]);U prefix=low(j),an=1ULL<<j;vector<int>ids;for(int t=0;t<256;t++)if(!(used[t]>>j&1))ids.push_back(t);
  double power=global?POWER:1+(POWER-1)*min(1.,max(0.,(j-SINGLE-3)/double(max(1,64-SINGLE-4))));
  double weight=global?0:MUST_WEIGHT*max(0.,1-(j-SINGLE)/8.);double pen=global?penalty:penalty*min(1.,(j-SINGLE+1)/8.);
  array<array<double,65>,65>gt;for(int c=0;c<=64;c++)for(int d=0;d<=64;d++)gt[c][d]=pow(c+weight*d,power)-pow(pen,power);
  auto gain=[&](U m,int t){return gt[pc(m&rem[t])][pc(m&minority[t])];};
  auto consider=[&](int p){auto bp=S[p];for(int t:ids)if(!((A[t]^bp.v)&bp.m&rem[t])){double g=gain(bp.m,t);if(g>bestgain[t]){bestgain[t]=g;bestcard[t]=p;}}};
  if(!global)for(int v=0;v<made[j];v++)consider(base[j]+v);
  for(int slot=made[j];slot<end;slot++){
   double best=-1;Paper bp{an,slot==1?an:0};
   auto eval=[&](U m,U v){double sum=0;for(int t:ids)if(!((A[t]^v)&m&rem[t]))sum+=max(0.,gain(m,t)-bestgain[t]);return sum;};
   auto update=[&](U m,U v){double z=eval(m,v);if(z>best){best=z;bp={m,v};}return z;};
   for(int st=0;st<starts&&!ids.empty();st++){if(solverCpu()>=solverTrainDeadline)break;
    int t=ids[rng()%ids.size()],color=slot<2?slot:((A[t]>>j)&1);if((rem[t]&an)&&int((A[t]>>j)&1)!=color)continue;
    U ones=A[t]&rem[t]&prefix,zeros=~A[t]&rem[t]&prefix,fill=A[t];
    auto pat=[&](U oo,U zz,bool dense){U m=(dense?(prefix&~(oo&zz)):(oo^zz))|an;U v=(oo&~zz)|(fill&~(oo|zz));v=(v&~an)|(color?an:0);return Paper{m,v&m};};
    for(int step=0;step<9;step++){
     auto p=pat(ones,zeros,true);double cur=update(p.m,p.v);p=pat(ones,zeros,false);cur=max(cur,update(p.m,p.v));double nxt=-1;U no=ones,nz=zeros;
     for(int z=0;z<probes;z++){int tt=ids[rng()%ids.size()];if((rem[tt]&an)&&int((A[tt]>>j)&1)!=color)continue;U oo=ones|(A[tt]&rem[tt]&prefix),zz=zeros|(~A[tt]&rem[tt]&prefix);auto pp=pat(oo,zz,true);double f=update(pp.m,pp.v);pp=pat(oo,zz,false);f=max(f,update(pp.m,pp.v));if(f>nxt){nxt=f;no=oo;nz=zz;}}
     if(nxt<0)break;if(nxt<cur&&step>2&&rng()%4)break;if(no==ones&&nz==zeros)break;ones=no;zeros=nz;
    }
   }
   S[base[j]+slot]=bp;consider(base[j]+slot);
  }
  made[j]=end;if(!global)for(int t:ids)commit(t);
 };
 for(int pass=0;pass<2;pass++){
  reset();for(int j=63;j>=HEAVY_START;j--)for(int v=0;v<made[j];v++)considerGlobal(base[j]+v);
  for(int j=63;j>=HEAVY_START;j--)trainGroup(j,pass==0?firstSlots:firstSlots+secondSlots,true);
  for(int t=0;t<256;t++)commit(t);
  double uu=0;for(auto u:rem)uu+=pc(u)/256.;cerr<<"global pass "<<pass<<" rem "<<uu<<" uses "<<accumulate(uses.begin(),uses.end(),0.)/256<<endl;
 }
 for(int j=63;j>=SINGLE;j--)trainGroup(j,gsz[j],false);
 double m=accumulate(uses.begin(),uses.end(),0.)/256,r=0;for(auto x:rem)r+=pc(x)/256.;cerr<<"learn m "<<m<<" r "<<r<<" modeled "<<(penalty*m+r)/2<<" gain "<<totalgain/512<<endl;
 int bad=0;for(int t=0;t<256;t++)bad+=guardCount[t]!=PAL;cerr<<"native incomplete "<<bad<<endl;cerr<<"residual per8 ";for(int b=0;b<8;b++){double z=0;for(auto x:rem)z+=pc((x>>(8*b))&255)/256.;cerr<<z<<" ";}cerr<<endl;
}

// End design2_tour_global_learn.hpp

struct NodeBase {
 U u=~U(0),used=0,flips=0;
 int e=0,n=0,cost=0;
 unsigned short q=0,tails=0;
 NativeOrder native{};
 double key=0;

};
struct BN:NodeBase {array<unsigned char,64>p{},at{};};
struct SN:NodeBase {array<unsigned char,20>p{},at{};};
static BN toFull(SN const&s){BN n;static_cast<NodeBase&>(n)=s;copy_n(s.p.begin(),s.n,n.p.begin());copy_n(s.at.begin(),s.n,n.at.begin());return n;}
struct BP {bool ok=false;int cost=INF;BN node;};
struct BH:Hub {
 NativeOrder nativeOrder{};array<unordered_map<U,int>,256>mismatchCache;
 long long lowchange=0,highout=0,prep=0;
 BH(){for(int i=0;i<PAL;i++)nativeOrder[i]=i;}
 int nativeDistance(NativeOrder const&goal){
  array<int,8>rank{};for(int i=0;i<PAL;i++)rank[nativeOrder[i]]=i;vector<int>tails;
  for(int i=0;i<PAL-1;i++){int x=rank[goal[i]];auto it=lower_bound(tails.begin(),tails.end(),x);if(it==tails.end())tails.push_back(x);else *it=x;}
  return PAL-1-int(tails.size())+(goal[PAL-1]!=nativeOrder[PAL-1]);
 }
 NativeInfo completeNative(NodeBase const&n,U target){
  auto adj=targetGraph(n.u,target,nativeOrder);array<int,8>rank{};for(int i=0;i<PAL;i++)rank[nativeOrder[i]]=i;
  int count=pc(n.q),last=-1;for(int i=0;i<count;i++){int v=rank[n.native[i]];if(last>=0)adj[last]|=1<<v;last=v;}
  if(last>=0)for(int v=0;v<PAL;v++)if(!(n.q>>v&1))adj[last]|=1<<rank[v];
  auto reach=adj;for(int k=0;k<PAL;k++)for(int i=0;i<PAL;i++)if(reach[i]>>k&1)reach[i]|=reach[k];
  NativeInfo out;for(int i=0;i<PAL;i++)if(reach[i]>>i&1)return out;
  int all=(1<<PAL)-1,sinks=0;for(int i=0;i<PAL;i++)if(!adj[i])sinks|=1<<i;bool bottomSink=sinks>>(PAL-1)&1;
  array<unsigned char,256>good{};good[0]=1;int best=-1,bn=-1;
  for(int m=0;m<=all;m++){if(m){int j=31-__builtin_clz(m),rest=m^(1<<j);good[m]=good[rest]&&!(reach[j]&rest);}if(good[m]&&(bottomSink||(sinks&~m))&&pc(m)>bn){bn=pc(m);best=m;}}
  if(best<0)abort();out.closure=PAL-bn;
  int goalLast;if(bottomSink&&(best>>(PAL-1)&1))goalLast=PAL-1;else goalLast=31-__builtin_clz(sinks&~best);
  auto graph=adj;int prev=-1;for(int i=0;i<PAL;i++)if(best>>i&1){if(prev>=0)graph[prev]|=1<<i;prev=i;}
  int remaining=all;for(int at=0;at<PAL;at++){int incoming=0;for(int i=0;i<PAL;i++)if(remaining>>i&1)incoming|=graph[i];int ready=remaining&~incoming;if(at<PAL-1)ready&=~(1<<goalLast);if(!ready)abort();int v=__builtin_ctz(ready);out.order[at]=nativeOrder[v];remaining^=1<<v;}
  for(int i=0;i<count;i++)if(out.order[i]!=n.native[i]){cerr<<"suffix prefix mismatch"<<endl;abort();}
  return out;
 }
 BP search(U target,int ti,int bw){
  BP out;array<int,64>op;op.fill(-1);for(int p:old)op[anchor[p]]=p;
  array<int,64>flip{};array<array<int,20>,64>access{};array<int,8>rank{};for(int i=0;i<PAL;i++)rank[nativeOrder[i]]=i;
  U wrong=(target^nativeWord(nativeOrder))&MUST;
  for(int j=SINGLE;j<64;j++){auto&v=group[j];if(op[j]>=0){access[j][slotof[op[j]]]=0;for(int k=0;k<(int)v.size();k++)access[j][slotof[v[k]]]=k;}else{flip[j]=color(v[0])!=int(target>>j&1);if(flip[j])wrong|=1ULL<<j;for(int k=0;k<(int)v.size();k++)access[j][slotof[v[k]]]=k;}}
  const int ALL=(1<<PAL)-1,E=PAL+64-SINGLE;
  auto&cache=mismatchCache[ti];
  auto mismatch=[&](U u){u&=MUST;auto it=cache.find(u);if(it!=cache.end())return it->second;auto adj=targetGraph(u,target,nativeOrder);int m=feedbackCost(adj)+pc(u&target&MUST&~EDGE_MASK);cache[u]=m;return m;};
  auto close=[&](auto&n){if(n.q==ALL){while(n.e<E){int j=SINGLE+n.e-PAL;U bit=1ULL<<j;if((n.u&bit)&&flip[j])break;n.u&=~bit;n.e++;}}n.key=pc(n.u&wrong&~MUST)+mismatch(n.u)+.02*pc(n.u);};
  {
   BN n;U covered=0;
   for(auto [j,v]:trainSequence[ti]){int p=base[j]+v;n.p[n.n]=p;n.at[n.n]=trainCut[ti][j];n.n++;n.used|=1ULL<<j;n.cost+=2+access[j][v];covered|=S[p].m;}
   n.native=trainedNative[ti];n.cost+=nativeDistance(n.native);
   for(int j=SINGLE;j<64;j++)if(!(covered>>j&1)&&flip[j]){n.flips|=1ULL<<j;n.cost++;}
   n.e=E;n.q=ALL;out={true,n.cost,n};
  }
  int bound=out.cost+1;vector<vector<SN>>buckets(bound);SN init;close(init);buckets[0].push_back(init);
  struct Compare{bool operator()(SN const&a,SN const&b)const{return a.key>b.key;}};
  for(int c=0;c<bound;c++){
   if(bw<=0||solverCpu()>=solverSearchDeadline){teacherFallbackQueries++;return out;}
   priority_queue<SN,vector<SN>,Compare>heap(Compare{},move(buckets[c]));unordered_set<U>seen;int expansions=0;
   auto add=[&](SN n){if(n.cost>=bound)return;close(n);if(n.cost==c){heap.push(move(n));return;}auto&b=buckets[n.cost];b.push_back(move(n));if((int)b.size()>bw*16){nth_element(b.begin(),b.begin()+bw*5,b.end(),[](auto const&a,auto const&b){return a.key<b.key;});b.resize(bw*5);}};
   while(!heap.empty()&&expansions<bw){
    SN n=heap.top();heap.pop();U h=n.u^(n.used*0x9e3779b97f4a7c15ULL)^(U(n.e)*0xd1b54a32d192ed03ULL)^(U(n.q*65536+(n.q==ALL?0:n.tails))*0x94d049bb133111ebULL);
    if(!seen.insert(h).second)continue;expansions++;
    if(n.e==E)return{true,n.cost,toFull(n)};
    U bad;int minanchor=SINGLE;
    if(n.q!=ALL){
     bad=n.u&MUST;int count=pc(n.q);
     if(!mismatch(n.u)){
      auto fin=completeNative(n,target);
      if(fin.closure<100){SN z=n;int paid=count-pc(n.tails);if(fin.closure<paid)abort();z.cost+=fin.closure-paid;z.native=fin.order;z.q=ALL;z.e=PAL;z.tails=0;z.u&=~MUST;add(z);}
     }
     for(int v=0;v<PAL;v++)if(!(n.q>>v&1)&&!((S[v].v^target)&S[v].m&n.u)){
      SN z=n;z.native[count]=v;z.q|=1<<v;z.u&=~S[v].m;z.e++;
      if(count==PAL-1)z.cost+=v!=nativeOrder[PAL-1];
      else{int r=rank[v],above=z.tails&~((1<<r)-1);if(above){z.tails^=1<<__builtin_ctz(above);z.cost++;}z.tails|=1<<r;}
      if(z.q==ALL)z.u&=~MUST;add(z);
     }
    }else{int j=SINGLE+n.e-PAL;bad=1ULL<<j;SN z=n;z.cost+=flip[j];z.flips|=bad;z.u&=~bad;z.e++;add(z);minanchor=j+1;}
    if(n.n>=18)continue;vector<int>good,badm;
    for(int j=minanchor;j<64;j++)if(!(n.used>>j&1))for(int v=0;v<gsz[j];v++){
     int p=base[j]+v;U b=(S[p].v^target)&S[p].m&n.u;
     if(S[p].m&bad){if(b){badm.push_back(p);continue;}SN z=n;z.u&=~S[p].m;z.used|=1ULL<<j;z.cost+=2+access[j][v];z.p[z.n]=p;z.at[z.n]=n.e;z.n++;add(z);}else if(!b&&(S[p].m&n.u))good.push_back(p);
    }
    for(int q:good){int a=anchor[q];U u=n.u&~S[q].m;int cq=2+access[a][slotof[q]];if(n.cost+cq+2>=bound)continue;for(int p:badm){int b=anchor[p];if(a==b||((S[p].v^target)&S[p].m&u))continue;SN z=n;z.u=u&~S[p].m;z.used|=(1ULL<<a)|(1ULL<<b);z.cost+=cq+2+access[b][slotof[p]];z.p[z.n]=q;z.at[z.n]=n.e;z.n++;z.p[z.n]=p;z.at[z.n]=n.e;z.n++;add(z);}}
   }
  }
  return out;
 }
 void reorderNative(NativeOrder const&goal){
  array<int,8>rank{};for(int i=0;i<PAL;i++)rank[nativeOrder[i]]=i;int best=0,bn=0;
  for(int mask=0;mask<(1<<(PAL-1));mask++){int last=-1;bool ok=true;for(int i=0;i<PAL-1;i++)if(mask>>i&1){int r=rank[goal[i]];if(r<last){ok=false;break;}last=r;}if(ok&&pc(mask)>bn){bn=pc(mask);best=mask;}}
  if(goal[PAL-1]!=nativeOrder[PAL-1]){mv(goal[PAL-1],PAL-1);lowchange++;}
  for(int i=PAL-2;i>=0;i--)if(!(best>>i&1)){before(goal[i],goal[i+1]);lowchange++;}nativeOrder=goal;
 }
 int runBG(U target,int ti,int bw){
  int oldn=old.size();long long initial=moves;BP best=search(target,ti,bw);auto n=best.node;
  array<int,64>pick;pick.fill(-1);array<int,192>seq,at;seq.fill(-1);at.fill(-1);for(int i=0;i<n.n;i++){int p=n.p[i];pick[anchor[p]]=p;seq[p]=i;at[p]=n.at[i];}
  for(auto it=old.rbegin();it!=old.rend();++it){int p=*it,j=anchor[p];auto&g=group[j];int q=g[0],desired=pick[j];if(desired<0)desired=color(p)==int(target>>j&1)?p:q;if(desired==p){before(p,q);g.insert(g.begin(),p);}else{int z=insert_pos(g,desired,p);after(p,g[z-1]);g.insert(g.begin()+z,p);}}old.clear();
  reorderNative(n.native);
  long long beforeprep=moves;for(int j=SINGLE;j<64;j++){if(pick[j]>=0)expose(j,pick[j]);else if(n.flips>>j&1){int desired=group[j][0];for(int p:group[j])if(color(p)==int(target>>j&1)){desired=p;break;}expose(j,desired);}}prep+=moves-beforeprep;
  vector<int>placed;for(int j=SINGLE;j<64;j++)if(pick[j]>=0){int p=pick[j],e=at[p];int ref=e<PAL?nativeOrder[e]:group[SINGLE+e-PAL][0],sr=100;for(int q:placed)if(at[q]==e&&seq[q]>seq[p]&&seq[q]<sr){ref=q;sr=seq[q];}before(p,ref);group[j].erase(group[j].begin());placed.push_back(p);old.push_back(p);}highout+=old.size();
  if(display()!=target){cerr<<"MIX WRONG "<<pc(display()^target)<<endl;abort();}int actual=moves-initial;if(actual-oldn+int(old.size())!=best.cost){cerr<<"MIX COST "<<actual-oldn+old.size()<<" predicted "<<best.cost<<endl;abort();}return actual;
 }
};

static vector<U> generateCatalog(uint64_t seed){
 mt19937_64 gen(seed);set<U>seen;vector<U>ans;
 while(ans.size()<256){U a=0;while(pc(a)<32)a|=1ULL<<(gen()%64);if(seen.insert(a).second)ans.push_back(a);}return ans;
}
static void chooseCoordinates(){
 vector<pair<int,int>>order;invertOriginal=0;
 for(int j=0;j<64;j++){int count=0;for(auto a:A)count+=(a>>j)&1;if(count>128)invertOriginal|=1ULL<<j;order.push_back({min(count,256-count),j});}
 sort(order.begin(),order.end());for(int j=0;j<64;j++)logicalToOriginal[j]=order[j].second;
 for(auto&a:A){U b=0;a^=invertOriginal;for(int j=0;j<64;j++)b|=((a>>logicalToOriginal[j])&1)<<j;a=b;}
}
static bool certifyDesign(){
 for(auto p:S)if(p.v&~p.m)return false;
 for(int j=SINGLE;j<64;j++){
  if(gsz[j]<2)return false;
  for(int v=0;v<gsz[j];v++){auto p=S[base[j]+v];if(!(p.m>>j&1)||(j<63&&(p.m>>(j+1))))return false;}
  if((S[base[j]].v>>j&1)!=0||(S[base[j]+1].v>>j&1)!=1)return false;
 }
 for(int t=0;t<256;t++){
  if(guardCount[t]!=PAL||trainSequence[t].size()>36)return false;
  U u=~U(0),used=0;int lastCut=0;
  for(auto [j,v]:trainSequence[t]){if(j<SINGLE||j>=64||v<0||v>=gsz[j]||(used>>j&1))return false;used|=1ULL<<j;if(trainCut[t][j]<lastCut||trainCut[t][j]>PAL)return false;lastCut=trainCut[t][j];}
  int nativeMask=0;
  for(int e=0;e<=PAL;e++){
   for(auto [j,v]:trainSequence[t])if(trainCut[t][j]==e){auto p=S[base[j]+v];if((p.v^A[t])&p.m&u)return false;u&=~p.m;}
   if(e<PAL){int k=trainedNative[t][e];if(k<0||k>=PAL||(nativeMask>>k&1))return false;nativeMask|=1<<k;auto p=S[k];if((p.v^A[t])&p.m&u)return false;u&=~p.m;}
  }
  if(u&MUST)return false;
 }
 return true;
}
static void universalDesign(vector<U>const&input){
 A=input;invertOriginal=0;iota(logicalToOriginal.begin(),logicalToOriginal.end(),0);
 S.fill({0,0});for(int j=0;j<64;j++){S[2*j]={1ULL<<j,0};S[2*j+1]={1ULL<<j,1ULL<<j};}
}
static array<Paper,192> restoredDesign(){
 array<Paper,192>result{};
 for(int p=0;p<192;p++)for(int j=0;j<64;j++)if(S[p].m>>j&1){int orig=logicalToOriginal[j];result[p].m|=1ULL<<orig;if(((S[p].v>>j)^(invertOriginal>>orig))&1)result[p].v|=1ULL<<orig;}
 return result;
}
int main(int argc,char**argv){
 ios::sync_with_stdio(false);cin.tie(nullptr);solverCpuStart=clock();
 bool selftest=argc>1&&string(argv[1])=="--selftest",makeInput=argc>1&&string(argv[1])=="--make-input";
 int seed=(selftest||makeInput)&&argc>2?atoi(argv[2]):0;
 if(selftest&&argc>3)solverCpuLimit=max(.10,atof(argv[3]));
 solverSearchDeadline=max(.05,solverCpuLimit-.04);solverTrainDeadline=min(1.17,solverCpuLimit*.65);
 int beam=selftest&&argc>4?max(0,atoi(argv[4])):128;
 int N=64,K=192,P=256,R=1024;vector<U>input;
 if(selftest||makeInput)input=generateCatalog(seed);
 else{
  if(!(cin>>N>>K>>P>>R))return 0;if(N!=64||K!=192||P!=256||R<1||R>1024)return 0;
  for(int t=0;t<P;t++){string row;if(!(cin>>row)||row.size()!=64)return 0;U a=0;for(int j=0;j<64;j++){if(row[j]=='1')a|=1ULL<<j;else if(row[j]!='0')return 0;}input.push_back(a);}
 }
 mt19937_64 requests(uint64_t(seed)+9817);
 if(makeInput){cout<<"64 192 256 1024\n";for(auto a:input){for(int j=0;j<64;j++)cout<<char('0'+((a>>j)&1));cout<<'\n';}int prev=-1;for(int r=0;r<1024;r++){int t;do{t=requests()%256;}while(t==prev);prev=t;cout<<t<<'\n';}return 0;}
 A=input;PAL=8;POWER=1.7;HEAVY_START=48;setup(28);G=PAL;GM[0]=MUST;FREQ=true;CLOSURE_BONUS=false;
 uint64_t designSeed=0x243f6a8885a308d3ULL;for(auto a:input)designSeed=seedMix(designSeed^a);rng.seed(designSeed);chooseCoordinates();
 initTournament();for(int j=63;j>=SINGLE;j--)LEARN_ORDER.push_back(j);learnAny(128,24,6);
 bool universal=!certifyDesign()||(getenv("FORCE_FALLBACK")&&atoi(getenv("FORCE_FALLBACK")));
 if(universal)universalDesign(input);
 double designCpu=solverCpu();auto physical=restoredDesign();BH hub;hub.record=true;hub.operations.reserve(384);
 if(!selftest){for(auto p:physical){for(int j=0;j<64;j++)cout<<(!(p.m>>j&1)?'.':char('0'+((p.v>>j)&1)));cout<<'\n';}cout.flush();}
 ofstream trace;if(getenv("TRACE_PATH")){trace.open(getenv("TRACE_PATH"));if(!trace)return 1;trace<<"{\"N\":64,\"K\":192,\"P\":256,\"R\":"<<R<<",\"patterns\":[";for(int p=0;p<192;p++){if(p)trace<<',';trace<<"[\""<<hex<<physical[p].m<<"\",\""<<physical[p].v<<dec<<"\"]";}trace<<"],\"targets\":[";for(int t=0;t<256;t++){if(t)trace<<',';trace<<'\"'<<hex<<input[t]<<dec<<'\"';}trace<<"]}\n";}
 int previous=-1,maximum=0;long long total=0,beamWork=0;U fallbackDisplay=0;
 for(int q=0;q<R;q++){
  int t;if(selftest){do{t=requests()%256;}while(t==previous);}else if(!(cin>>t)||t<0)return 0;
  if(t>=256)return 0;previous=t;hub.operations.clear();int cost;
  if(universal){U diff=fallbackDisplay^input[t];while(diff){int j=__builtin_ctzll(diff);diff&=diff-1;int paper=2*j+int(fallbackDisplay>>j&1);hub.mv(paper,2*j+1);fallbackDisplay^=1ULL<<j;}cost=hub.operations.size();if(hub.display()!=input[t])abort();}
  else{int effectiveBeam=beam;double elapsedOnline=solverCpu()-designCpu,remaining=solverSearchDeadline-solverCpu();if(beamWork>0&&elapsedOnline>0){double perBeam=elapsedOnline/beamWork;effectiveBeam=min(beam,max(32,int(remaining/max(1,R-q)/perBeam)));}if(remaining<=0)effectiveBeam=0;beamWork+=effectiveBeam;cost=hub.runBG(A[t],t,effectiveBeam);}
  if(cost!=(int)hub.operations.size()||cost>384)abort();total+=cost;maximum=max(maximum,cost);
  if(!selftest){cout<<cost<<'\n';for(auto [paper,depth]:hub.operations)cout<<paper<<' '<<depth<<'\n';cout.flush();}
  if(trace.is_open()){trace<<"{\"target\":"<<t<<",\"moves\":[";for(int i=0;i<(int)hub.operations.size();i++){if(i)trace<<',';trace<<'['<<hub.operations[i].first<<','<<hub.operations[i].second<<']';}trace<<"]}\n";}
 }
  // [移植] 統計を `名前 = 数値` の形で stderr に出す（observe.py stats 用）。
 if(!selftest)cerr<<"design_cpu = "<<designCpu<<"\ntotal_cpu = "<<solverCpu()<<"\nuniversal = "<<universal<<"\nteacher_fallback_queries = "<<teacherFallbackQueries<<"\nmean_beam = "<<beamWork/double(R)<<"\n";
 if(selftest)cout<<setprecision(12)<<"RESULT TOURNAMENT_PRODUCTION seed "<<seed<<" avg "<<total/double(R)<<" total "<<total<<" max "<<maximum<<" universal "<<universal<<" teacherFallbackQueries "<<teacherFallbackQueries<<" meanBeam "<<beamWork/double(R)<<" designCpu "<<designCpu<<" totalCpu "<<solverCpu()<<'\n';
 else if(getenv("PROFILE"))cerr<<setprecision(12)<<"PROFILE total "<<total<<" avg "<<total/double(R)<<" max "<<maximum<<" universal "<<universal<<" teacherFallbackQueries "<<teacherFallbackQueries<<" meanBeam "<<beamWork/double(R)<<" designCpu "<<designCpu<<" totalCpu "<<solverCpu()<<endl;
 return 0;
}
