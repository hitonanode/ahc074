#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using U=std::uint64_t;
using Bits=std::array<U,4>;
struct Group{std::vector<int>targets;U diff=0;};
struct Pattern{unsigned white,black;};
struct Free{
 int M,G,S=0,Q=0,words=0;bool clipped=false;
 std::array<U,256>A{};std::vector<Group>groups,best_groups;
 std::vector<std::array<unsigned char,8>>perms;
 std::vector<Pattern>patterns;std::vector<U>table;
 std::array<Bits,63>care{},desired{};
 std::array<Bits,4>weighted{};
 std::array<int,256>chosen{};
 std::array<int,63>map{},best_map{};
 std::vector<U>display;
 std::array<U,8>opaque{},black{};
 U gm=0;std::mt19937_64 rng;
 double best_obj=1e100;
 Free(const std::string&path,int m,int g,unsigned seed,int triple_limit):M(m),G(g),rng(seed){
  assert(3<=M&&M<=8&&G<=63);
#include "ctor.inc"
  for(int j=0;j<63;j++)for(int t=0;t<256;t++)if(A[t]>>j&1)desired[j][t/64]|=1ULL<<(t%64);
  std::array<unsigned char,8>p0{};std::iota(p0.begin(),p0.begin()+M,0);
  do{perms.push_back(p0);}while(std::next_permutation(p0.begin(),p0.begin()+M));
  S=perms.size();words=(S+63)/64;display.resize(S);
  for(unsigned o=3;o<(1U<<M);o++)for(unsigned b=(o-1)&o;b;b=(b-1)&o)patterns.push_back({o^b,b});
  Q=patterns.size();table.resize(Q*words);
  for(int q=0;q<Q;q++)for(int s=0;s<S;s++){
   auto pat=patterns[q];for(int j=0;j<M;j++)if((pat.white|pat.black)>>perms[s][j]&1){
    if(pat.black>>perms[s][j]&1)table[q*words+s/64]|=1ULL<<(s%64);break;
   }
  }
  std::vector<int>pairs;for(int q=0;q<Q;q++)if(std::popcount(patterns[q].white|patterns[q].black)==2)pairs.push_back(q);
  std::vector<int>w(63);std::iota(w.begin(),w.end(),0);std::shuffle(w.begin(),w.end(),rng);
  map.fill(-1);for(int j=0;j<G;j++)map[w[j]]=pairs[rng()%pairs.size()];
  refresh_groups();rebuild();
 }
 double uniform(){return std::generate_canonical<double,53>(rng);}
 double noise(double temperature){return temperature*std::log(std::max(1e-14,uniform()));}
 bool shown(int q,int s)const{return table[q*words+s/64]>>(s%64)&1;}
 void refresh_groups(){
  care={};for(auto&g:groups){g.diff=0;for(int t:g.targets)g.diff|=A[t]^A[g.targets[0]];
   for(int t:g.targets)for(U z=g.diff;z;z&=z-1){int j=std::countr_zero(z);care[j][t/64]|=1ULL<<(t%64);}
  }
 }
 void rebuild(){
  gm=0;opaque={};black={};std::fill(display.begin(),display.end(),0);
  for(int j=0;j<63;j++)if(map[j]>=0){
   gm|=1ULL<<j;auto p=patterns[map[j]];
   for(int k=0;k<M;k++){if((p.white|p.black)>>k&1)opaque[k]|=1ULL<<j;if(p.black>>k&1)black[k]|=1ULL<<j;}
   for(int s=0;s<S;s++)if(shown(map[j],s))display[s]|=1ULL<<j;
  }
 }
 int minimum(int t,U holes)const{
  int best=64;holes&=gm;
  for(U value:display){best=std::min(best,std::popcount((value^A[t])&holes));if(!best)break;}
  return best;
 }
 // Greedily place any sheet that is correct on all still exposed windows.
 // Any valid order has such a first sheet, and its removal preserves feasibility.
 bool feasible(U target,U holes)const{
  holes&=gm;unsigned used=0;
  for(int pass=0;pass<M&&holes;pass++){
   bool progress=false;
   for(int k=0;k<M;k++)if(!(used>>k&1)&&!((target^black[k])&opaque[k]&holes)){
    used|=1U<<k;holes&=~opaque[k];progress=true;
   }
   if(!progress)return false;
  }
  return !holes;
 }
 int pick(int t,U holes,double temp){
  std::array<int,64>count{};int best=64;holes&=gm;
  for(U value:display){int e=std::popcount((value^A[t])&holes);count[e]++;best=std::min(best,e);}
  int level=best;
  if(temp>1e-7){std::array<double,64>w{};double total=0;
   for(int e=best;e<64;e++)if(count[e]){w[e]=count[e]*std::exp(-(e-best)/temp);total+=w[e];}
   double skip=uniform()*total;for(level=best;level<63;level++){if(skip<w[level])break;skip-=w[level];}
  }
  int skip=rng()%count[level];
  for(int s=0;s<S;s++)if(std::popcount((display[s]^A[t])&holes)==level&&skip--==0)return s;
  assert(false);return 0;
 }
 void choose_orders(double temperature){
  weighted={};
  for(auto&g:groups)if(g.targets.size()>1){
   int err=0;for(int t:g.targets)err+=minimum(t,g.diff);
   int weight=clipped?std::max(0,3-err):0;
   for(int t:g.targets){chosen[t]=pick(t,g.diff,temperature);weighted[weight][t/64]|=1ULL<<(t%64);}
  }
 }
 double score(Group&g,double penalty)const{
  g.diff=0;for(int t:g.targets)g.diff|=A[t]^A[g.targets[0]];
  if(g.targets.size()<2)return 0;
  int errors=0;for(int t:g.targets)errors+=minimum(t,g.diff);
  double e=clipped?2*(1-std::exp(-errors*.7)):errors;
  return penalty*e+g.targets.size()*(.4*std::popcount(g.diff&~gm)+.1*std::popcount(g.diff&gm));
 }
 void change_groups(double penalty,double temperature,int trials){
  std::vector<double>cost(groups.size());for(int i=0;i<int(groups.size());i++)cost[i]=score(groups[i],penalty);
  for(int it=0;it<trials;it++){
   int x=rng()%groups.size(),y=rng()%groups.size();if(x==y||groups[x].targets.size()+groups[y].targets.size()==2)continue;
   auto a=groups[x],b=groups[y];std::swap(a.targets[rng()%a.targets.size()],b.targets[rng()%b.targets.size()]);
   double sa=score(a,penalty),sb=score(b,penalty),delta=sa+sb-cost[x]-cost[y];
   if(delta<=0||delta<-noise(temperature)){groups[x]=a;groups[y]=b;cost[x]=sa;cost[y]=sb;}
  }
  refresh_groups();
 }
 void choose_mapping(double penalty,double temperature){
  std::vector<Bits>above(Q);for(int q=0;q<Q;q++)for(int t=0;t<256;t++)if(shown(q,chosen[t]))above[q][t/64]|=1ULL<<(t%64);
  std::array<int,63>best{};std::array<double,63>gain{};
  for(int j=0;j<63;j++){
   int total=0;for(U x:care[j])total+=std::popcount(x);
   double least=1e100;
   for(int q=0;q<Q;q++){
    int wrong=0;for(int k=0;k<4;k++){
     U diff=(above[q][k]^desired[j][k])&care[j][k];
     if(!clipped)wrong+=std::popcount(diff);else for(int b=0;b<4;b++)wrong+=(1<<b)*std::popcount(diff&weighted[b][k]);
    }
    double value=penalty*wrong+noise(temperature);
    // Among equal fits, prefer sparse windows for visibility and reversibility.
    value+=.002*std::popcount(patterns[q].white|patterns[q].black);
    if(value<least)least=value,best[j]=q;
   }
   gain[j]=least-.3*total-noise(temperature);
  }
  std::array<int,63>w{};std::iota(w.begin(),w.end(),0);std::sort(w.begin(),w.end(),[&](int a,int b){return gain[a]<gain[b];});
  map.fill(-1);for(int i=0;i<G;i++)map[w[i]]=best[w[i]];
 }
 std::array<int,4>measure()const{
  int errors=0,valid=0,triples=0,handles=0;
  for(auto&g:groups)if(g.targets.size()>1){int e=0;for(int t:g.targets)e+=minimum(t,g.diff);errors+=e;
   if(!e){valid+=g.targets.size()-1;triples+=g.targets.size()==3;}
   handles+=g.targets.size()*std::popcount(g.diff&~gm);
  }
  return {errors,valid,triples,handles};
 }
 std::array<int,2>catalog()const{
  std::array<std::array<bool,256>,256>ok{};int pairs=0,triples=0;
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){
   U d=A[a]^A[b];bool v=feasible(A[a],d)&&feasible(A[b],d);ok[a][b]=v;pairs+=v;
  }
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(ok[a][b])for(int c=b+1;c<256;c++)if(ok[a][c]&&ok[b][c]){
   U d=(A[a]^A[b])|(A[a]^A[c]);if(std::popcount(d)<=40&&feasible(A[a],d)&&feasible(A[b],d)&&feasible(A[c],d))triples++;
  }
  return {pairs,triples};
 }
};
int main(int argc,char**argv){
 if(argc<2)return 2;
 int M=argc>2?std::stoi(argv[2]):6,G=argc>3?std::stoi(argv[3]):38;
 double seconds=argc>4?std::stod(argv[4]):120;unsigned seed=argc>5?std::stoul(argv[5]):1812831;
 int triples=argc>6?std::stoi(argv[6]):10;bool clipped=argc>7?std::stoi(argv[7]):false;
 auto start=std::chrono::steady_clock::now();auto elapsed=[&](){return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
 Free x(argv[1],M,G,seed,triples);x.clipped=clipped;int iterations=0;
 for(int it=0;elapsed()<seconds;it++){
  int phase=it%200;double f=phase/199.,temperature=1.5*std::pow(.02/1.5,f),penalty=4*std::pow(16.,f);
  if(it&&phase==0){x.map=x.best_map;x.groups=x.best_groups;x.refresh_groups();x.rebuild();}
  x.change_groups(penalty,temperature*penalty*.25,80);
  x.choose_orders(temperature);x.choose_mapping(penalty,temperature*penalty*.25);x.rebuild();
  auto st=x.measure();double value=clipped?-10000*st[1]+100*st[0]+.3*st[3]:1000*st[0]+.3*st[3];
  if(value<x.best_obj){x.best_obj=value;x.best_map=x.map;x.best_groups=x.groups;
   std::cerr<<"best "<<it<<" errors "<<st[0]<<" valid_merges "<<st[1]<<" triples "<<st[2]<<" handles "<<st[3]<<" seconds "<<elapsed()<<'\n';
  }
  iterations=it+1;if(!st[0])break;
 }
 x.map=x.best_map;x.groups=x.best_groups;x.refresh_groups();x.rebuild();auto st=x.measure();auto cat=x.catalog();
 // Independent feasibility implementations must agree on the selected groups.
 for(auto&g:x.groups)for(int t:g.targets)assert(x.feasible(x.A[t],g.diff)==(x.minimum(t,g.diff)==0));
 std::cout<<std::setprecision(12)<<"{\"M\":"<<M<<",\"G\":"<<G<<",\"iterations\":"<<iterations<<",\"errors\":"<<st[0]<<",\"valid_merges\":"<<st[1]<<",\"valid_triples\":"<<st[2]<<",\"pairs\":"<<cat[0]<<",\"catalog\":"<<cat[1]<<",\"seconds\":"<<elapsed()<<",\"patterns\":[";
 for(int j=0;j<63;j++){if(j)std::cout<<',';if(x.map[j]<0)std::cout<<"null";else{auto p=x.patterns[x.map[j]];std::cout<<'['<<p.white<<','<<p.black<<']';}}
 std::cout<<"],\"groups\":[";bool first=true;for(auto&g:x.groups){if(!first)std::cout<<',';first=false;std::cout<<'[';for(int i=0;i<int(g.targets.size());i++){if(i)std::cout<<',';std::cout<<g.targets[i];}std::cout<<']';}std::cout<<"]}\n";
}
