// Layered Barcode Display: a complete reactive C++17 solver.
// Fixed parameters: N=64, K=192, P=256. No external files or libraries required.
//
// Core invariant: paper group h always paints h and has holes at j<h.
// Reserve groups are ordered by decreasing h. Active papers form a prefix.
// A new prefix paper must agree with the target outside already covered bits.
// Every moved paper is checked for visibility before it is moved.
//
// Design: 2 singleton papers at bit63; 6 papers per anchor0..15;
// 2 papers per anchor16..62. First learn low-anchor patterns, then learn
// patterns for residual target bits, treating covered positions as don't-care.
// Query planning: a guaranteed completion, greedy prefix candidates, then a
// width64/depth8 beam over the covered-bit mask. Moves are counted exactly.
//
// Design learning uses only the256 targets given before the requests.
// The solver reads exactly one request at a time.
// Use --stats to write initialization timing to stderr.
// This implementation has not demonstrated 12 moves/query.
// Port: <bits/stdc++.h> replaced by individual headers (Clang support).
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
using namespace std;using U=uint64_t;
struct Move{int p,d;};
struct Solver{
 int H=63,B,C=192;array<U,192>mask{},value{};array<int,192>order{},pos{},group{};
 vector<vector<int>> groups;vector<U>A;int active=-1;vector<int> actives;vector<Move>moves;
 int learning=7,listpolicy=0,multi=1,allocation=2;double futureweight=0.5;mt19937 rng{42};
 array<bool,192> primary{};
 int beamwidth=64,beamdepth=8,protectdata=0;
 void positions(){for(int i=0;i<192;i++)pos[order[i]]=i;}
 void init(){B=2*(64-H);C=192-B;groups.assign(H,{});group.fill(-1);active=-1;actives.clear();moves.clear();
  for(int j=H;j<64;j++)for(int c=0;c<2;c++){int p=2*(j-H)+c;mask[p]=1ull<<j;value[p]=(U)c<<j;}
  vector<bool> used(A.size());
  vector<int> extras(H);
  int width=allocation==1?min(H,24):allocation==2?min(H,16):allocation==3?min(H,8):H;
  for(int i=0;i<32;i++)extras[i%width]++;
  if(allocation==4&&H>=24){fill(extras.begin(),extras.end(),0);for(int h=0;h<8;h++)extras[h]=2;for(int h=8;h<24;h++)extras[h]=1;}
  int p=B;
  for(int h=H-1;h>=0;h--)for(int q=0;q<2+2*extras[h];q++,p++){
   group[p]=h;groups[h].push_back(p);
   int t=-1;for(int i=0;i<(int)A.size();i++)if(!used[i]&&int(A[i]>>h&1)==(q&1)){t=i;break;}
   if(t<0)for(int i=0;i<(int)A.size();i++)if(int(A[i]>>h&1)==(q&1)){t=i;break;}
   if(t>=0){used[t]=true;value[p]=A[t]&(~0ull<<(h+1));}
   value[p]|=(U)(q&1)<<h;mask[p]=~0ull<<h;
  }
  learn_stages();
  iota(order.begin(),order.end(),0);positions();
 }
 void learn_stages(){
  const int T=A.size();vector<U> fixed(T);array<int,192> role{};
  for(int h=0;h<H;h++)for(int q=0;q<(int)groups[h].size();q++){
   int p=groups[h][q];
   if(learning==5)role[p]=h>=24?0:h>=8?1:2;
   else if(learning==7)role[p]=h<16?0:1;
   else if(learning==8)role[p]=h<24?0:1;
   else if(learning==9)role[p]=h<8?0:1;
   else role[p]=min(q/2,2);
  }
  struct Candidate{U m,v;int cl;array<int8_t,256> gain;};
  for(int stage=0;stage<3;stage++){
   vector<Candidate> pool;vector<int> quota(2*H),owner(192),papers;
   for(int p=B;p<192;p++)if(role[p]==stage){owner[p]=2*group[p]+int(value[p]>>group[p]&1);quota[owner[p]]++;papers.push_back(p);}
   if(papers.empty())continue;
   for(int h=0;h<H;h++)for(int col=0;col<2;col++)if(quota[2*h+col]){
    const U scope=~0ull<<(h+1);vector<int> ids;vector<U> z(T),o(T);
    for(int t=0;t<T;t++)if(!(fixed[t]>>h&1)&&int(A[t]>>h&1)==col){ids.push_back(t);z[t]=~A[t]&~fixed[t]&scope;o[t]=A[t]&~fixed[t]&scope;}
    set<pair<U,U>> patterns;
    auto addpattern=[&](U zz,U oo,U ref){U m=scope&~(zz&oo);U v=(oo|(ref&~zz))&m;patterns.insert({m,v});};
    for(int t:ids){
     addpattern(z[t],o[t],A[t]);vector<pair<int,int>> near;
     for(int u:ids)if(u!=t)near.push_back({__builtin_popcountll((z[t]|z[u])&(o[t]|o[u])),u});
     sort(near.begin(),near.end());
     for(int i=0;i<min(4,(int)near.size());i++){
      int u=near[i].second;U zz=z[t]|z[u],oo=o[t]|o[u];vector<int> picked{t,u};addpattern(zz,oo,A[t]);
      for(int count=3;count<=6;count++){
       int bu=-1,bscore=1000;
       for(int v:ids)if(find(picked.begin(),picked.end(),v)==picked.end()){
        int s=__builtin_popcountll((zz|z[v])&(oo|o[v]));if(s<bscore){bscore=s;bu=v;}
       }
       if(bu<0)break;picked.push_back(bu);zz|=z[bu];oo|=o[bu];addpattern(zz,oo,A[t]);
      }
     }
    }
    if(patterns.empty())patterns.insert({0,0});
    for(auto [m,v]:patterns){
     Candidate c;c.m=m;c.v=v;c.cl=2*h+col;c.gain.fill(0);
     for(int t:ids)if(!((A[t]^v)&m&~fixed[t]))c.gain[t]=max(0,__builtin_popcountll(m&~fixed[t])+1-(int)groups[h].size()-3);
     pool.push_back(c);
    }
   }
   array<int,256> best{};vector<int> chosen;vector<bool>used(pool.size());priority_queue<pair<int,int>>queue;
   for(int i=0;i<(int)pool.size();i++){int g=0;for(int t=0;t<T;t++)g+=pool[i].gain[t];queue.push({g,i});}
   while(chosen.size()<papers.size()&&!queue.empty()){
    auto [upper,i]=queue.top();queue.pop();auto&c=pool[i];if(!quota[c.cl]||used[i])continue;
    int g=0;for(int t=0;t<T;t++)g+=max(0,int(c.gain[t])-best[t]);
    while(!queue.empty()&&(!quota[pool[queue.top().second].cl]||used[queue.top().second]))queue.pop();
    if(!queue.empty()&&g<queue.top().first){queue.push({g,i});continue;}
    chosen.push_back(i);used[i]=true;quota[c.cl]--;for(int t=0;t<T;t++)best[t]=max(best[t],int(c.gain[t]));
   }
   vector<vector<int>>byclass(2*H);for(int i=0;i<(int)pool.size();i++)byclass[pool[i].cl].push_back(i);
   for(int pass=0;pass<2;pass++)for(int&pick:chosen){
    best.fill(0);for(int i=0;i<(int)chosen.size();i++)if(&chosen[i]!=&pick){int q=chosen[i];for(int t=0;t<T;t++)best[t]=max(best[t],int(pool[q].gain[t]));}
    int bg=-1,bi=pick;for(int i:byclass[pool[pick].cl]){int g=0;for(int t=0;t<T;t++)g+=max(0,int(pool[i].gain[t])-best[t]);if(g>bg){bg=g;bi=i;}}
    pick=bi;
   }
   for(int p:papers){
    auto it=find_if(chosen.begin(),chosen.end(),[&](int i){return pool[i].cl==owner[p];});if(it==chosen.end())continue;auto c=pool[*it];chosen.erase(it);
    mask[p]=c.m|(1ull<<group[p]);value[p]=c.v|(value[p]&(1ull<<group[p]));
   }
   for(int t=0;t<T;t++){
    int bs=0,bp=-1;
    for(int p:papers)if(!(fixed[t]>>group[p]&1)&&!((A[t]^value[p])&mask[p]&~fixed[t])){
     int score=__builtin_popcountll(mask[p]&~fixed[t])-(int)groups[group[p]].size()-3;
     if(score>bs){bs=score;bp=p;}
    }
    if(bp>=0)fixed[t]|=mask[bp];
   }
  }
 }

 U display(array<U,192>*vis=nullptr)const{U seen=0,v=0;if(vis)vis->fill(0);for(int p:order){U n=mask[p]&~seen;if(vis)(*vis)[p]=n;v|=n&value[p];seen|=mask[p];}return v;}
 void move(int p,int d){array<U,192>vis;display(&vis);if(!vis[p]){cerr<<"illegal "<<p<<"\n";abort();}int s=pos[p];if(s==d)return;if(s<d)for(int i=s;i<d;i++)order[i]=order[i+1];else for(int i=s;i>d;i--)order[i]=order[i-1];order[d]=p;positions();moves.push_back({p,d});}
 int head(int h)const{int b=groups[h][0];for(int p:groups[h])if(pos[p]<pos[b])b=p;return b;}
 int tail(int h)const{int b=groups[h][0];for(int p:groups[h])if(pos[p]>pos[b])b=p;return b;}
 int firstCorrect(int h,U a)const{int b=-1;for(int p:groups[h])if(!((value[p]^a)>>h&1)&&(b<0||pos[p]<pos[b]))b=p;assert(b>=0);return b;}
 void expose(int target){int h=group[target],after=target;while(head(h)!=target){int p=head(h);move(p,pos[listpolicy?after:tail(h)]);after=p;}}
 vector<Move> solve(U a){
  moves.clear();
  if(active>=0){actives.push_back(active);active=-1;}
  for(int old:actives){
   int h=group[old],d=192;for(int p:groups[h])if(p!=old)d=min(d,pos[p]-1);
   if((a^value[old])>>h&1)d=pos[tail(h)];
   move(old,d);
  }
  actives.clear();
  U base=display(),wrong=(base^a)&(~0ull<<H);int handlecost=0;vector<int> handlefix(H);
  for(int h=0;h<H;h++){int right=firstCorrect(h,a);for(int p:groups[h])if(pos[p]<pos[right])handlefix[h]++;handlecost+=handlefix[h];}
  int besttotal=handlecost+__builtin_popcountll(wrong),bestp=-1,bestcut=0;
  for(int p=B;p<192;p++){
   int h=group[p];if((value[p]^a)&mask[p]&((1ull<<H)-1))continue;
   int rank=0;for(int q:groups[h])rank+=pos[q]<pos[p];
   int hc=handlecost+rank+1;for(int h2=0;h2<H;h2++)if(mask[p]>>h2&1)hc-=handlefix[h2];
   U m=mask[p]&(~0ull<<H),bad=(a^value[p])&m,good=m&~bad;
   int cost=__builtin_popcountll(bad)+__builtin_popcountll(bad&wrong)+__builtin_popcountll(wrong&~m);
   if(hc+cost<besttotal){besttotal=hc+cost;bestp=p;bestcut=0;}
   for(int c=0;c<B;c++){
    int q=order[c],j=H+q/2;U b=1ull<<j;
    if((value[q]^a)&b){if((wrong&good)&b&&pos[q]<pos[q^1])cost++;}
    else if(bad&b)cost--;
    if(hc+cost<besttotal){besttotal=hc+cost;bestp=p;bestcut=c+1;}
   }
  }
  vector<int> bestmulti;bool bestprotect=false;
  if(multi){
   double bestscore=besttotal+(bestp>=0?futureweight:0);
   if(bestp>=0&&handlecost+__builtin_popcountll(wrong)<bestscore){bestscore=handlecost+__builtin_popcountll(wrong);bestp=-1;besttotal=(int)bestscore;}
   array<int,192> extra{};array<U,192> bad{};
   vector<int> starts{-1};
   for(int p=B;p<192;p++){
    int rank=0;for(int q:groups[group[p]])rank+=pos[q]<pos[p];extra[p]=rank+1;bad[p]=(a^value[p])&mask[p];
    if(!bad[p])starts.push_back(p);
   }
   auto remaining=[&](U covered){int z=__builtin_popcountll(wrong&~covered);for(int h=0;h<H;h++)if(!(covered>>h&1))z+=handlefix[h];return z;};
   for(int start:starts){
    vector<int> chosen;U covered=0;int actual=0;
    if(start>=0){chosen.push_back(start);actual+=extra[start];covered|=mask[start];}
    for(;;){
     int bp=-1;double bg=0;int before=remaining(covered);
     for(int p=B;p<192;p++)if(!(covered>>group[p]&1)&&!(bad[p]&~covered)){
      double gain=before-remaining(covered|mask[p])-extra[p]-futureweight;
      if(gain>bg){bg=gain;bp=p;}
     }
     if(bp<0)break;chosen.push_back(bp);actual+=extra[bp];covered|=mask[bp];
    }
    actual+=remaining(covered);double score=actual+futureweight*chosen.size();
    if(score<bestscore){bestscore=score;bestmulti=chosen;}
   }
  }
  if(multi){
   // The beam uses the same exact exposure ranks and terminal completion cost.
   double bestscore=besttotal+(bestp>=0?futureweight:0);
   array<int,192> extra{};array<U,192> bad{};
   for(int p=B;p<192;p++){int rank=0;for(int q:groups[group[p]])rank+=pos[q]<pos[p];extra[p]=rank+1;bad[p]=(a^value[p])&mask[p];}
   auto remaining=[&](U covered){int z=__builtin_popcountll(wrong&~covered);for(int h=0;h<H;h++)if(!(covered>>h&1))z+=handlefix[h];return z;};
   if(!bestmulti.empty()){U f=0;int c=0;for(int p:bestmulti){c+=extra[p];f|=mask[p];}bestscore=c+remaining(f)+futureweight*bestmulti.size();}
   // A planning state needs only the covered windows.  Eligible groups have not
   // been touched, so their exposure ranks remain the ranks at query start.
   if(beamwidth>0){
    struct BeamState{
     U covered=0;int actual=0,remaining=0;
     array<unsigned char,8> path{};
    };
    for(int protected_mode=0;protected_mode<1;protected_mode++){
    vector<BeamState> beam(1);beam[0].covered=protected_mode?(1ull<<63):0;
    beam[0].actual=protected_mode?__builtin_popcountll(wrong&(1ull<<63)):0;beam[0].remaining=remaining(beam[0].covered);
    const int depthlimit=min({beamdepth,H,8});
    for(int depth=0;depth<depthlimit&&!beam.empty();depth++){
     vector<BeamState> cand;cand.reserve(beam.size()*24);
     unordered_map<U,int> seen;seen.reserve(beam.size()*32+1);
     for(const auto &node:beam)for(int p=B;p<192;p++){
      if((node.covered>>group[p]&1)||(bad[p]&~node.covered))continue;
      int cost=node.actual+extra[p];
      if(cost+futureweight*(depth+1)>=bestscore-1e-10)continue;
      U cover=node.covered|mask[p];
      auto it=seen.find(cover);
      if(it!=seen.end()&&cand[it->second].actual<=cost)continue;
      BeamState next=node;next.covered=cover;next.actual=cost;
      next.remaining=remaining(cover);next.path[depth]=p;
      double score=cost+next.remaining+futureweight*(depth+1);
      if(score<bestscore-1e-10){
       bestscore=score;bestprotect=protected_mode;bestmulti.assign(next.path.begin(),next.path.begin()+depth+1);
      }
      if(it==seen.end()){seen[cover]=cand.size();cand.push_back(next);}
      else cand[it->second]=next;
     }
     auto cmp=[](const BeamState &x,const BeamState &y){
      int xs=x.actual+x.remaining,ys=y.actual+y.remaining;
      if(xs!=ys)return xs<ys;
      int xc=__builtin_popcountll(x.covered),yc=__builtin_popcountll(y.covered);
      if(xc!=yc)return xc>yc;
      if(x.actual!=y.actual)return x.actual<y.actual;
      return x.covered<y.covered;
     };
     if(int(cand.size())>beamwidth){
      nth_element(cand.begin(),cand.begin()+beamwidth,cand.end(),cmp);
      cand.resize(beamwidth);
     }
     sort(cand.begin(),cand.end(),cmp);beam=std::move(cand);
    }
    }
   }

  }
  if(!bestmulti.empty()){
   U cover=0;int depth=0;
   for(int p:bestmulti){assert(!(cover>>group[p]&1));assert(!((value[p]^a)&mask[p]&~cover));expose(p);move(p,depth++);cover|=mask[p];}
   for(int h=0;h<H;h++)if(!(cover>>h&1))expose(firstCorrect(h,a));
   for(int j=H;j<64;j++)if(!(cover>>j&1)){int right=2*(j-H)+((a>>j)&1),bad=right^1;if(pos[bad]<pos[right])move(bad,pos[right]);}
   actives=bestmulti;
   if(display()!=a){cerr<<"residual prefix fail\n";abort();}return moves;
  }
  for(int h=0;h<H;h++)if(bestp<0||!(mask[bestp]>>h&1)){
   expose(firstCorrect(h,a));
  }
  if(bestp<0){
   for(int j=H;j<64;j++){int right=2*(j-H)+((a>>j)&1),bad=right^1;if(pos[bad]<pos[right])move(bad,pos[right]);}
  }else{
   int h=group[bestp];expose(bestp);
   vector<bool>prefix(B);for(int i=0;i<bestcut;i++)prefix[order[i]]=true;
   U m=mask[bestp]&(~0ull<<H),bad=(a^value[bestp])&m;
   for(int j=H;j<64;j++){
    U b=1ull<<j;int right=2*(j-H)+((a>>j)&1),wr=right^1;
    if(!(m&b)){if(pos[wr]<pos[right]){prefix[wr]=false;move(wr,pos[right]);}continue;}
    if(bad&b){
     if(pos[wr]<pos[right]){prefix[wr]=false;move(wr,pos[right]);}
     if(!prefix[right]){move(right,0);prefix[right]=true;}
    }else if(prefix[wr]&&pos[wr]<pos[right]){prefix[wr]=false;move(wr,pos[right]);}
   }
   int d=0;for(int p=0;p<B;p++)if(prefix[p])d=max(d,pos[p]+1);
   move(bestp,d);active=bestp;
  }
  if(display()!=a){cerr<<"bad display H="<<H<<" chosen="<<bestp<<" cut="<<bestcut<<" predicted="<<besttotal<<" actual="<<moves.size()<<" diff="<<hex<<(display()^a)<<dec<<"\n";abort();}
  return moves;
 }
};
int main(int argc, char **argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    bool stats=false;
    for(int i=1;i<argc;i++) {
        if(string(argv[i])=="--stats") stats=true;
        else return 1;
    }
    int n,k,p,r;
    if(!(cin>>n>>k>>p>>r)) return 0;
    if(n!=64 || k!=192 || p!=256 || r<0) return 1;
    Solver solver;
    solver.A.resize(p);
    for(auto &a:solver.A) {
        string s;
        if(!(cin>>s) || s.size()!=64) return 1;
        a=0;
        for(int j=0;j<64;j++) {
            if(s[j]=='1') a|=1ull<<j;
            else if(s[j]!='0') return 1;
        }
    }
    clock_t started=clock();
    solver.init();
    // Port: always printed (originally only with --stats), in the "name = value" form.
    (void)stats;
    cerr<<"design_cpu_seconds = "<<double(clock()-started)/CLOCKS_PER_SEC<<"\n";
    for(int id=0;id<192;id++) {
        for(int j=0;j<64;j++) {
            cout<<((solver.mask[id]>>j&1)?char('0'+(solver.value[id]>>j&1)):'.');
        }
        cout<<'\n';
    }
    cout.flush();
    for(int q=0;q<r;q++) {
        int t;
        if(!(cin>>t) || t==-1) return 0;
        if(t<0 || t>=p) return 1;
        auto answer=solver.solve(solver.A[t]);
        if(answer.size()>384) return 1;
        cout<<answer.size()<<'\n';
        for(auto m:answer) cout<<m.p<<' '<<m.d<<'\n';
        cout.flush();
    }
    return 0;
}
