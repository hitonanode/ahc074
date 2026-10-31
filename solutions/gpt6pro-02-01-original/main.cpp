// Experimental solver for AHC074: Layered Barcode Display.
// All decisions use only the target catalogue and queries already received.
// Default: 64 anchor groups with sizes 2 (0..39), 4 (40..47), 5 (48..63).
// Each paper has non-holes only at coordinates <= its anchor. Its anchor
// is always opaque. The first two native papers of a group have opposite
// anchor colours. This makes native-bit correction and ascending-anchor
// promotion legal. Old promoted papers return in descending anchor order.
// A paper inserted before native group cut affects only bits >= cut.
// The planner learns a shared partial-pattern dictionary and searches
// compatible partial covers, including two-paper protection steps.
//
// Build: g++ -std=c++17 -O3 layered_barcode_original.cpp -o solver
// Submission: ./solver                 (reactive protocol)
// Test: ./solver --selftest SEED [CPU_BUDGET=1.75] [LAYOUT=4] [BEAM=32]
// Self-test uses independent RNG streams for targets, learning and requests.
// A finite CPU budget reduces planning, with an exact legal native fallback.
// This is an experimental ~15 move solver, not a proven 10 move solution.
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
using namespace std;
bool verbose=false; int hillPasses=8; double cpuLimit=1.75,learnLimit=.72;
clock_t cpuStart; double cpuSeconds(){return double(clock()-cpuStart)/CLOCKS_PER_SEC;}
using U=uint64_t;int pc(U x){return __builtin_popcountll(x);} 
struct Paper{U m=0,v=0;};array<Paper,192>S;vector<U>A;mt19937_64 rng; array<int,64>base,gsz; array<int,192>anchor,slotof; array<int,192>importance{}; bool FREQ=false; int layout=0;
void setup(int mode){layout=mode;int k=0;for(int j=0;j<64;j++){gsz[j]=mode==0?3:(mode==1?(j<32?2:4):(mode==2?(j<48?2:6):(mode==3?(j<56?2:10):(mode==4?(j<40?2:(j<48?4:5)):(j<16?2:(j<48?3:4))))));base[j]=k;for(int v=0;v<gsz[j];v++){anchor[k]=j;slotof[k]=v;k++;}}if(k!=192)abort();}
U low(int j){return j==63?~U(0):((U(1)<<(j+1))-1);}
void learn(int starts,int probes,double penalty){
 // Initialise every group to a valid two-colour fallback before learning.
 for(int j=0;j<64;j++)for(int v=0;v<gsz[j];v++)S[base[j]+v]={U(1)<<j,(v&1)?U(1)<<j:0};
 vector<U>rem(256,~U(0));vector<int>uses(256);double totalgain=0;
 for(int j=63;j>=0;j--){
  U prefix=low(j),an=U(1)<<j;vector<double>bestgain(256,0);vector<int>choice(256,-1);
  for(int slot=0;slot<gsz[j];slot++){
   double best=-1;Paper bp{an,slot==1?an:0};
   auto eval=[&](U m,U v){double sum=0;for(int t=0;t<256;t++)if(!((A[t]^v)&m&rem[t]))sum+=max(0.,pc(m&rem[t])-penalty-bestgain[t]);return sum;};
   auto update=[&](U m,U v){double z=eval(m,v);if(z>best){best=z;bp={m,v};}return z;};
   for(int st=0;st<starts;st++){ if(cpuSeconds()>learnLimit)break;
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
   int hill=hillPasses;
   for(int it=0;it<hill && cpuSeconds()<learnLimit;it++){Paper from=bp,next=bp;double score=best;
    for(int b=0;b<=j;b++){if(b==j&&slot<2)continue;U bit=U(1)<<b;int old=(from.m&bit)?((from.v&bit)?2:1):0;for(int nc=0;nc<3;nc++){if(nc==old||(b==j&&nc==0))continue;U mm=(from.m&~bit)|(nc?bit:0),vv=(from.v&~bit)|(nc==2?bit:0);double z=eval(mm,vv);if(z>score){score=z;next={mm,vv};}}}
    if(score<=best)break;bp=next;best=score;
   }
   S[base[j]+slot]=bp;
   for(int t=0;t<256;t++)if(!((A[t]^bp.v)&bp.m&rem[t])){double g=pc(bp.m&rem[t])-penalty;if(g>bestgain[t]){bestgain[t]=g;choice[t]=slot;}}
  }
  for(int t=0;t<256;t++)if(choice[t]>=0){importance[base[j]+choice[t]]++;rem[t]&=~S[base[j]+choice[t]].m;uses[t]++;totalgain+=bestgain[t];}
 }
 if(verbose){double m=accumulate(uses.begin(),uses.end(),0.)/256,r=0;for(auto x:rem)r+=pc(x)/256.;cerr<<"learn m "<<m<<" r "<<r<<" modeled "<<(penalty*m+r)/2<<" gain "<<totalgain/512<<"\n";
 cerr<<"residual per 8bits ";for(int b=0;b<8;b++){double z=0;for(auto x:rem)z+=pc((x>>(8*b))&255)/256.;cerr<<z<<" ";}cerr<<"\n";}
}
bool INTERVAL=false, BRIDGE=false;
struct Plan{U u,sel0,sel1,sel2,sel3;int cost;double key;array<unsigned char,64>cut{};array<unsigned char,64>seq{};};
struct Hub{
 array<vector<int>,64> group;vector<int>old;
 array<int,192>ord;long long moves=0;bool check=true; vector<pair<int,int>> operations; int truncated=0;
 Hub(){iota(ord.begin(),ord.end(),0);for(int j=0;j<64;j++){for(int v=0;v<gsz[j];v++)group[j].push_back(base[j]+v);}}
 U display(){U cov=0,v=0;for(int p:ord){v|=S[p].v&~cov;cov|=S[p].m;}return v;}
 void mv(int k,int d){int pos=find(ord.begin(),ord.end(),k)-ord.begin();if(check){U cov=0;for(int i=0;i<pos;i++)cov|=S[ord[i]].m;if(!(S[k].m&~cov)){cerr<<"ILLEGAL "<<k<<" d "<<d<<"\n";abort();}}if(pos<d)move(ord.begin()+pos+1,ord.begin()+d+1,ord.begin()+pos);else if(pos>d)move_backward(ord.begin()+d,ord.begin()+pos,ord.begin()+pos+1);ord[d]=k;moves++;operations.emplace_back(k,d);}
 void before(int k,int ref){int p=find(ord.begin(),ord.end(),k)-ord.begin(),r=find(ord.begin(),ord.end(),ref)-ord.begin();mv(k,r-(p<r));}
 void after(int k,int ref){int p=find(ord.begin(),ord.end(),k)-ord.begin(),r=find(ord.begin(),ord.end(),ref)-ord.begin();mv(k,r+1-(p<r));}
 int color(int p){return (S[p].v>>anchor[p])&1;}
 int insert_pos(vector<int>const&g,int p,int x){int at=find(g.begin(),g.end(),p)-g.begin()+1;bool opp=at<(int)g.size()&&color(g[at])!=color(p);if(color(x)!=color(p)&&(!opp||importance[x]>importance[g[at]]))return at;if(opp)at++;while(at<(int)g.size()&&importance[g[at]]>=importance[x])at++;return at;}
 void expose(int j,int p){auto&g=group[j];while(g[0]!=p){int x=g[0];g.erase(g.begin());int ix=find(g.begin(),g.end(),p)-g.begin();int at=FREQ?insert_pos(g,p,x):(color(x)!=color(p)?ix+1:g.size());after(x,g[at-1]);g.insert(g.begin()+at,x);}if(color(g[0])==color(g[1])){cerr<<"head invariant fail j "<<j<<" p "<<p<<"\n";abort();}}
 int run(U target,int bw,double beta){
  operations.clear();long long initial=moves;array<int,64>prev;prev.fill(-1);for(int p:old)prev[anchor[p]]=p;
  array<int,64>flip;array<array<int,10>,64>access;U wrong=0;
  for(int j=0;j<64;j++){
   auto&g=group[j];if(prev[j]>=0){flip[j]=0;int p=prev[j];access[j][slotof[p]]=0;for(int ix=0;ix<(int)g.size();ix++)access[j][slotof[g[ix]]]=ix;}
   else{flip[j]=color(g[0])!=int(target>>j&1);for(int ix=0;ix<gsz[j];ix++)access[j][slotof[g[ix]]]=ix;if(flip[j])wrong|=U(1)<<j;}
  }
  Plan plan;
  if(INTERVAL){
   array<vector<Plan>,65>buckets;int bestcost=pc(wrong);plan={0,0,0,0,0,bestcost,0};
   auto normalize=[&](Plan&n){U ww=n.u&wrong;if(!ww){n.u=0;return 64;}int at=__builtin_ctzll(ww);if(at)n.u&=~low(at-1);return at;};
   Plan init{~U(0),0,0,0,0,0,0};int ii=normalize(init);buckets[ii].push_back(init);
   for(int i=0;i<64 && bw>0;i++){
    if(cpuSeconds()>cpuLimit){truncated++;break;}
    auto&bucket=buckets[i];sort(bucket.begin(),bucket.end(),[](auto&a,auto&b){return a.key<b.key;});vector<Plan>beam;unordered_set<U>seen;
    for(auto&n:bucket){U used=n.sel0|n.sel1|n.sel2|n.sel3;U h=n.u^(used*0x9e3779b97f4a7c15ULL);if(seen.insert(h).second){beam.push_back(n);if((int)beam.size()==bw)break;}}vector<Plan>().swap(bucket);
    auto add=[&](Plan n){if(n.cost>=bestcost)return;int ni=normalize(n);if(ni==64){bestcost=n.cost;plan=n;return;}n.key=n.cost+beta*pc(n.u&wrong);buckets[ni].push_back(n);if(buckets[ni].size()>size_t(bw*16)){auto&v=buckets[ni];nth_element(v.begin(),v.begin()+bw*4,v.end(),[](auto&a,auto&b){return a.key<b.key;});v.resize(bw*4);}};
    for(auto n:beam){Plan nn=n;nn.cost+=flip[i];nn.u&=~(U(1)<<i);add(nn);U used=n.sel0|n.sel1|n.sel2|n.sel3;
     for(int a=i+1;a<64;a++)if(!(used>>a&1))for(int v=0;v<gsz[a];v++){int p=base[a]+v;if(!(S[p].m>>i&1)||((S[p].v^target)&S[p].m&n.u))continue;nn=n;nn.u&=~S[p].m;nn.cost+=2+access[a][v];int code=v+1;if(code&1)nn.sel0|=U(1)<<a;if(code&2)nn.sel1|=U(1)<<a;if(code&4)nn.sel2|=U(1)<<a;if(code&8)nn.sel3|=U(1)<<a;nn.cut[a]=i;nn.seq[a]=pc(used);add(nn);}
     if(BRIDGE && n.cost+4<bestcost){
      vector<int>good,badmain;for(int a=i+1;a<64;a++)if(!(used>>a&1))for(int v=0;v<gsz[a];v++){int p=base[a]+v;U bad=(S[p].v^target)&S[p].m&n.u;if(S[p].m>>i&1){if(bad)badmain.push_back(p);}else if(!bad&&(S[p].m&n.u)&&n.cost+4+access[a][v]<bestcost)good.push_back(p);}
      for(int q:good){int a=anchor[q],v=slotof[q];int cq=2+access[a][v];U uq=n.u&~S[q].m;
       for(int p:badmain){int b=anchor[p],w=slotof[p];if(a==b||((S[p].v^target)&S[p].m&uq))continue;int cp=2+access[b][w];if(n.cost+cq+cp>=bestcost)continue;Plan z=n;z.u=uq&~S[p].m;z.cost+=cq+cp;
        int c=v+1;if(c&1)z.sel0|=U(1)<<a;if(c&2)z.sel1|=U(1)<<a;if(c&4)z.sel2|=U(1)<<a;if(c&8)z.sel3|=U(1)<<a;z.cut[a]=i;z.seq[a]=pc(used);
        c=w+1;if(c&1)z.sel0|=U(1)<<b;if(c&2)z.sel1|=U(1)<<b;if(c&4)z.sel2|=U(1)<<b;if(c&8)z.sel3|=U(1)<<b;z.cut[b]=i;z.seq[b]=pc(used)+1;add(z);
       }
      }
     }
    }
   }
  }else{
  vector<Plan>beam{{~U(0),0,0,0,0,0,0}};
  for(int j=63;j>=0;j--){vector<Plan>cand;cand.reserve(beam.size()*(gsz[j]+1));U bit=U(1)<<j;
   for(auto n:beam){for(int v=-1;v<gsz[j];v++){
     Plan nn=n;if(v>=0){auto&p=S[base[j]+v];if((p.v^target)&p.m&n.u)continue;nn.u&=~p.m;nn.cost+=2+access[j][v];int code=v+1;if(code&1)nn.sel0|=bit;if(code&2)nn.sel1|=bit;if(code&4)nn.sel2|=bit;if(code&8)nn.sel3|=bit;}
     if(nn.u&bit)nn.cost+=flip[j];nn.u&=~bit;nn.key=nn.cost+beta*pc(nn.u&wrong);cand.push_back(nn);
   }}
   sort(cand.begin(),cand.end(),[](auto&a,auto&b){return a.key<b.key;});beam.clear();unordered_set<U>seen;seen.reserve(bw*2+1);for(auto&n:cand)if(seen.insert(n.u).second){beam.push_back(n);if((int)beam.size()==bw)break;}
  }
  plan=*min_element(beam.begin(),beam.end(),[](auto&a,auto&b){return a.cost<b.cost;});
  }
  array<int,64>pick;pick.fill(-1);U covered=0;for(int j=0;j<64;j++){int c=((plan.sel0>>j)&1)+2*((plan.sel1>>j)&1)+4*((plan.sel2>>j)&1)+8*((plan.sel3>>j)&1);if(c){pick[j]=base[j]+c-1;U mm=S[pick[j]].m;if(INTERVAL&&plan.cut[j])mm&=~low(plan.cut[j]-1);covered|=mm;}}
  // Undo old promotions, each is currently the topmost remaining promoted card.
  for(auto it=old.rbegin();it!=old.rend();++it){int p=*it,j=anchor[p];auto&g=group[j];int q=g[0],r=g[1];int desired=pick[j];
   if(desired<0)desired=color(p)==int(target>>j&1)?p:q;
   if(desired==p){before(p,q);g.insert(g.begin(),p);}
   else{int at=FREQ?insert_pos(g,desired,p):int(find(g.begin(),g.end(),desired)-g.begin()+1);after(p,g[at-1]);g.insert(g.begin()+at,p);}
  }

  old.clear();
  // All local rotations happen in the hub before any promotion.
  for(int j=0;j<64;j++){
   if(pick[j]>=0)expose(j,pick[j]);
   else if(!(covered>>j&1)){int desired=group[j][0];if(color(desired)!=int(target>>j&1)){for(int q:group[j])if(color(q)==int(target>>j&1)){desired=q;break;}}expose(j,desired);}
   else if(color(group[j][0])==color(group[j][1])){cerr<<"unused bad heads\n";abort();}
  }
  for(int j=0;j<64;j++)if(pick[j]>=0){int p=pick[j];if(INTERVAL){int ref=group[plan.cut[j]][0],sr=100;for(int a=0;a<j;a++)if(pick[a]>=0&&plan.cut[a]==plan.cut[j]&&plan.seq[a]>plan.seq[j]&&plan.seq[a]<sr){sr=plan.seq[a];ref=pick[a];}before(p,ref);}else mv(p,0);group[j].erase(group[j].begin());old.push_back(p);}
  if(check && display()!=target){cerr<<"WRONG display "<<pc(display()^target)<<"\n";abort();}
  int actual=moves-initial;int amort=actual-(int)prevcount(prev)+(int)old.size();
  if(check && amort!=plan.cost){cerr<<"COST mismatch "<<amort<<" predicted "<<plan.cost<<" actual "<<actual<<"\n";abort();}
  return actual;
 }
 int prevcount(array<int,64>const&prev){int n=0;for(int p:prev)n+=p>=0;return n;}
};

static uint64_t mix64(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
int main(int argc,char**argv){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 bool selftest=argc>1&&string(argv[1])=="--selftest";
 int seed=selftest&&argc>2?atoi(argv[2]):0;
 int mode=selftest&&argc>4?atoi(argv[4]):4;
 int beam=selftest&&argc>5?atoi(argv[5]):32;
 if(selftest&&argc>3)cpuLimit=atof(argv[3]);
 int N=64,K=192,P=256,R=1024;
 mt19937_64 gen(mix64(seed)),queries(mix64(uint64_t(seed)^0xa4093822299f31d0ULL));
 if(selftest){
  set<U>seen;while(A.size()<256){U a=0;while(pc(a)<32)a|=U(1)<<(gen()%64);if(seen.insert(a).second)A.push_back(a);}
 }else{
  if(!(cin>>N>>K>>P>>R))return 0;
  if(N!=64||K!=192||P!=256)return 0;
  for(int t=0;t<P;t++){string str;cin>>str;if(str.size()!=64)return 0;U a=0;for(int j=0;j<64;j++)if(str[j]=='1')a|=U(1)<<j;A.push_back(a);}
 }
 verbose=selftest;cpuStart=clock();auto wallStart=chrono::steady_clock::now();
 setup(mode);INTERVAL=BRIDGE=FREQ=true;
 U designSeed=0x243f6a8885a308d3ULL;for(auto a:A)designSeed=mix64(designSeed^a);rng.seed(designSeed);
 learnLimit=min(.72,cpuLimit*.43);learn(64,16,6.0);double learnCpu=cpuSeconds();
 Hub h;h.check=selftest;
 if(!selftest){for(auto p:S){for(int j=0;j<64;j++)cout<<(!(p.m>>j&1)?'.':(p.v>>j&1)?'1':'0');cout<<'\n';}cout.flush();}
 int prev=-1,mx=0;long long total=0;double active=0;
 for(int r=0;r<R;r++){
  int t;if(selftest){do{t=queries()%256;}while(t==prev);}else{if(!(cin>>t)||t==-1)return 0;if(t<0||t>=P)return 0;}prev=t;
  int bw=cpuSeconds()>=cpuLimit?0:beam;
  int count=h.run(A[t],bw,.8);total+=count;mx=max(mx,count);active+=h.old.size();
  if(count>2*K||count!=(int)h.operations.size()){cerr<<"invalid operation count\n";return 1;}
  if(!selftest){cout<<count<<'\n';for(auto [k,d]:h.operations)cout<<k<<' '<<d<<'\n';cout.flush();}
 }
  // [移植] 統計を `名前 = 数値` の形で stderr に出す（observe.py stats 用）。
 if(!selftest)cerr<<"learn_cpu = "<<learnCpu<<"\ntotal_cpu = "<<cpuSeconds()<<"\nactive_papers = "<<active/R<<"\ntruncated = "<<h.truncated<<"\n";
 if(selftest)cout<<fixed<<setprecision(6)<<"seed="<<seed<<" layout="<<mode<<" beam="<<beam<<" avg="<<double(total)/R<<" max="<<mx<<" errors=0"<<" active="<<active/R<<" learn_cpu="<<learnCpu<<" total_cpu="<<cpuSeconds()<<" wall="<<chrono::duration<double>(chrono::steady_clock::now()-wallStart).count()<<" truncated="<<h.truncated<<'\n';
 return 0;
}
