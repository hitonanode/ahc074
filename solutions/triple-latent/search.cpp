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
struct Mapping{std::array<int,63>edge{},color{};};
struct Latent{
 int M=8,G=38,ne=28,S=0;
 std::array<U,256>A{};std::vector<Group>groups;
 std::vector<std::pair<int,int>>edges;
 std::vector<std::array<unsigned char,9>>perms;
 std::vector<U> comparisons;std::vector<int>reversed;
 std::array<Bits,63>care{},desired{};
 std::array<int,256>chosen{};
 std::vector<U>display;
 std::mt19937_64 rng{0x712e819abdULL};
 Mapping map,best_map;int best_errors=100000,best_valid=0;
 std::vector<Group>best_groups;
 double best_obj=1e100;
 explicit Latent(const std::string&path,int m,int g,unsigned seed):M(m),G(g),ne(m*(m-1)/2),rng(seed){
  assert(M<=9&&G>=ne&&G<=63);
  std::ifstream in(path);int p,n;in>>p>>n;assert(p==256);
  for(auto&a:A)in>>a;
  for(int i=0;i<n;i++){Group x;int size;in>>size;x.targets.resize(size);for(int&t:x.targets)in>>t;groups.push_back(x);}
  assert(in);
  // Two additional generic papers require two additional merges compared with
  // the six-paper seed. Choose close remaining singletons for these pairs.
  while(int(groups.size())>191-M){
   int a=-1,b=-1,bd=100;
   for(int i=0;i<int(groups.size());i++)if(groups[i].targets.size()==1)
    for(int j=i+1;j<int(groups.size());j++)if(groups[j].targets.size()==1){
     int d=std::popcount(A[groups[i].targets[0]]^A[groups[j].targets[0]]);
     if(d<bd)bd=d,a=i,b=j;
    }
   assert(a>=0);groups[a].targets.push_back(groups[b].targets[0]);groups.erase(groups.begin()+b);
  }
  for(auto&x:groups){
   for(int t:x.targets)x.diff|=A[t]^A[x.targets[0]];
   for(int t:x.targets)for(U z=x.diff;z;z&=z-1){int j=std::countr_zero(z);care[j][t/64]|=1ULL<<(t%64);}
  }
  for(int j=0;j<63;j++)for(int t=0;t<256;t++)if(A[t]>>j&1)desired[j][t/64]|=1ULL<<(t%64);
  for(int a=0;a<M;a++)for(int b=a+1;b<M;b++)edges.emplace_back(a,b);
  std::array<unsigned char,9>p0{};std::iota(p0.begin(),p0.begin()+M,0);
  do{
   std::array<int,9>pos{};for(int i=0;i<M;i++)pos[p0[i]]=i;
   U mask=0;for(int e=0;e<ne;e++)if(pos[edges[e].first]<pos[edges[e].second])mask|=1ULL<<e;
   comparisons.push_back(mask);perms.push_back(p0);
  }while(std::next_permutation(p0.begin(),p0.begin()+M));
  S=perms.size();display.resize(S);reversed.resize(S);
  for(int s=0;s<S;s++){auto p1=perms[s];std::reverse(p1.begin(),p1.begin()+M);reversed[s]=std::lower_bound(perms.begin(),perms.end(),p1)-perms.begin();}
  map.edge.fill(-1);std::vector<int>w(63);std::iota(w.begin(),w.end(),0);std::shuffle(w.begin(),w.end(),rng);
  for(int j=0;j<G;j++)map.edge[w[j]]=j%ne,map.color[w[j]]=rng()&1;
 }
 double uniform(){return std::generate_canonical<double,53>(rng);}
 double noise(double t){return t*std::log(std::max(1e-14,uniform()));}
 void refresh_groups(){
  care={};
  for(auto&x:groups){
   x.diff=0;for(int t:x.targets)x.diff|=A[t]^A[x.targets[0]];
   for(int t:x.targets)for(U z=x.diff;z;z&=z-1){int j=std::countr_zero(z);care[j][t/64]|=1ULL<<(t%64);}
  }
 }
 // Minimum number of violated windows for one partial target. Appending v
 // last violates exactly the requested arcs from v to an earlier vertex.
 int minimum_errors(int target,U holes)const{
  std::array<std::array<int,9>,9>w{};
  for(U z=holes&generic_mask();z;z&=z-1){int j=std::countr_zero(z);auto[a,b]=edges[map.edge[j]];if((A[target]>>j&1)!=unsigned(map.color[j]))std::swap(a,b);w[a][b]++;}
  std::array<std::array<int,512>,9>row{};
  for(int v=0;v<M;v++)for(unsigned mask=1;mask<(1U<<M);mask++){int u=std::countr_zero(mask);row[v][mask]=row[v][mask&(mask-1)]+w[v][u];}
  std::array<int,512>dp{};
  for(unsigned mask=1;mask<(1U<<M);mask++){
   int best=100000;for(unsigned z=mask;z;z&=z-1){int v=std::countr_zero(z);unsigned rest=mask^(1U<<v);best=std::min(best,dp[rest]+row[v][rest]);}dp[mask]=best;
  }
  return dp[(1U<<M)-1];
 }
 double group_score(Group&x,double penalty)const{
  x.diff=0;for(int t:x.targets)x.diff|=A[t]^A[x.targets[0]];
  if(x.targets.size()<2)return 0;
  int errors=0;
  if(x.targets.size()==2)errors=2*minimum_errors(x.targets[0],x.diff);
  else for(int t:x.targets)errors+=minimum_errors(t,x.diff);
  U gm=generic_mask();int n=x.targets.size();
  return penalty*errors+n*(.4*std::popcount(x.diff&~gm)+.10*std::popcount(x.diff&gm));
 }
 void change_groups(double penalty,double temperature,int trials){
  std::vector<double>score(groups.size());for(int i=0;i<int(groups.size());i++)score[i]=group_score(groups[i],penalty);
  for(int it=0;it<trials;it++){
   int x=rng()%groups.size(),y=rng()%groups.size();if(x==y||groups[x].targets.size()+groups[y].targets.size()==2)continue;
   Group a=groups[x],b=groups[y];std::swap(a.targets[rng()%a.targets.size()],b.targets[rng()%b.targets.size()]);
   double sa=group_score(a,penalty),sb=group_score(b,penalty),delta=sa+sb-score[x]-score[y];
   if(delta<=0||delta<-noise(temperature)){groups[x]=a;groups[y]=b;score[x]=sa;score[y]=sb;}
  }
  refresh_groups();
 }
 void rebuild(){
  std::array<std::array<U,2>,36>mask{};
  for(int j=0;j<63;j++)if(map.edge[j]>=0)mask[map.edge[j]][map.color[j]]|=1ULL<<j;
  for(int s=0;s<S;s++){U shown=0,cmp=comparisons[s];for(int e=0;e<ne;e++)shown|=mask[e][cmp>>e&1];display[s]=shown;}
 }
 U generic_mask()const{U mask=0;for(int j=0;j<63;j++)if(map.edge[j]>=0)mask|=1ULL<<j;return mask;}
 int pick(int t,U holes,double temp,int scale){
  std::array<int,64>count{};int min=64;
  for(U show:display){int errors=std::popcount((show^A[t])&holes);count[errors]++;min=std::min(min,errors);}
  int level=min;
  if(temp>1e-7){
   std::array<double,64>weight{};double total=0;
   for(int e=min;e<64;e++)if(count[e]){weight[e]=count[e]*std::exp(-(e-min)*scale/temp);total+=weight[e];}
   double q=uniform()*total;for(level=min;level<63;level++){if(q<weight[level])break;q-=weight[level];}
  }
  int skip=rng()%count[level];
  for(int s=0;s<S;s++)if(std::popcount((display[s]^A[t])&holes)==level){if(skip--==0)return s;}
  assert(false);return -1;
 }
 void choose_orders(double temp){
  U gm=generic_mask();
  for(auto&x:groups)if(x.targets.size()>1){
   U holes=x.diff&gm;
   if(x.targets.size()==2){int a=x.targets[0],b=x.targets[1];chosen[a]=pick(a,holes,temp,2);chosen[b]=reversed[chosen[a]];}
   else for(int t:x.targets)chosen[t]=pick(t,holes,temp,1);
  }
 }
 static std::vector<int> assignment(const std::array<std::array<double,63>,63>&a){
  constexpr int n=63;std::array<double,n+1>u{},v{};std::array<int,n+1>p{},way{};
  for(int i=1;i<=n;i++){
   p[0]=i;int j0=0;std::array<double,n+1>minv;minv.fill(1e100);std::array<bool,n+1>used{};
   do{
    used[j0]=true;int i0=p[j0],j1=0;double delta=1e100;
    for(int j=1;j<=n;j++)if(!used[j]){double cur=a[i0-1][j-1]-u[i0]-v[j];if(cur<minv[j])minv[j]=cur,way[j]=j0;if(minv[j]<delta)delta=minv[j],j1=j;}
    for(int j=0;j<=n;j++)if(used[j])u[p[j]]+=delta,v[j]-=delta;else minv[j]-=delta;
    j0=j1;
   }while(p[j0]);
   do{int j1=way[j0];p[j0]=p[j1];j0=j1;}while(j0);
  }
  std::vector<int>result(n);for(int j=1;j<=n;j++)result[p[j]-1]=j-1;return result;
 }
 void choose_mapping(double penalty,double temp){
  std::array<Bits,36>above{};
  for(int t=0;t<256;t++)for(int e=0;e<ne;e++)if(comparisons[chosen[t]]>>e&1)above[e][t/64]|=1ULL<<(t%64);
  std::array<std::array<double,63>,63>cost{};
  std::array<std::array<int,36>,63>polarity{};
  std::array<int,63>bestedge{};
  for(int j=0;j<63;j++){
   int total=0;for(U x:care[j])total+=std::popcount(x);
   double minimum=1e100;int be=-1;
   for(int e=0;e<ne;e++){
    int wrong=0;for(int k=0;k<4;k++)wrong+=std::popcount((above[e][k]^desired[j][k])&care[j][k]);
    double c1=penalty*wrong+noise(temp),c0=penalty*(total-wrong)+noise(temp);
    int b=c1<c0;polarity[j][e]=b;cost[j][e]=std::min(c0,c1)+.10*total;
    if(cost[j][e]<minimum)minimum=cost[j][e],be=e;
   }
   bestedge[j]=be;
   for(int k=ne;k<G;k++)cost[j][k]=minimum;
   double handle=.4*total+noise(temp);
   for(int k=G;k<63;k++)cost[j][k]=handle;
  }
  auto assigned=assignment(cost);
  map.edge.fill(-1);
  for(int j=0;j<63;j++)if(assigned[j]<G){int e=assigned[j]<ne?assigned[j]:bestedge[j];map.edge[j]=e;map.color[j]=polarity[j][e];}
 }
 std::array<int,4> measure(){
  U gm=generic_mask();int errors=0,valid_merges=0,valid_triples=0,handles=0;
  for(auto&x:groups)if(x.targets.size()>1){
   int err=0;for(int t:x.targets){int min=64;for(U show:display)min=std::min(min,std::popcount((show^A[t])&x.diff&gm));err+=min;}
   errors+=err;handles+=x.targets.size()*std::popcount(x.diff&~gm);
   if(!err){valid_merges+=x.targets.size()-1;valid_triples+=x.targets.size()==3;}
  }
  return {errors,valid_merges,valid_triples,handles};
 }
 int catalog()const{
  U gm=generic_mask();
  auto feasible=[&](U target,U holes){
   std::array<unsigned,9>reach{};
   for(U z=holes&gm;z;z&=z-1){int j=std::countr_zero(z);auto[a,b]=edges[map.edge[j]];if((target>>j&1)!=unsigned(map.color[j]))std::swap(a,b);reach[a]|=1U<<b;}
   for(int k=0;k<M;k++)for(int a=0;a<M;a++)if(reach[a]>>k&1)reach[a]|=reach[k];
   for(int a=0;a<M;a++)if(reach[a]>>a&1)return false;
   return true;
  };
  std::array<std::array<bool,256>,256>ok{};
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)ok[a][b]=feasible(A[a],A[a]^A[b]);
  int count=0;
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++)if(ok[a][b])for(int c=b+1;c<256;c++)if(ok[a][c]&&ok[b][c]){
   U d=(A[a]^A[b])|(A[a]^A[c]);if(std::popcount(d)>40)continue;
   if(feasible(A[a],d)&&feasible(A[b],d)&&feasible(A[c],d))count++;
  }
  return count;
 }
};
int main(int argc,char**argv){
 if(argc<2)return 2;int M=argc>2?std::stoi(argv[2]):8,G=argc>3?std::stoi(argv[3]):38;double seconds=argc>4?std::stod(argv[4]):60;unsigned seed=argc>5?std::stoul(argv[5]):1812831;bool joint=argc>6?std::stoi(argv[6]):false;
 auto start=std::chrono::steady_clock::now();auto elapsed=[&](){return CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();};
 Latent x(argv[1],M,G,seed);x.rebuild();int iterations=0;
 for(int it=0;elapsed()<seconds;it++){
  int phase=it%200;double f=phase/199.;double temp=1.5*std::pow(.02/1.5,f),penalty=4*std::pow(16.,f);
  if(it&&phase==0){x.map=x.best_map;x.groups=x.best_groups;x.refresh_groups();x.rebuild();}
  if(joint)x.change_groups(penalty,temp*penalty*.25,200);
  x.choose_orders(temp);x.choose_mapping(penalty,temp*penalty*.25);x.rebuild();
  auto stats=x.measure();double value=1000*stats[0]+.3*stats[3];
  if(value<x.best_obj){x.best_obj=value;x.best_errors=stats[0];x.best_valid=stats[2];x.best_map=x.map;x.best_groups=x.groups;std::cerr<<"best "<<it<<" errors "<<stats[0]<<" valid_merges "<<stats[1]<<" triples "<<stats[2]<<" handles "<<stats[3]<<" seconds "<<elapsed()<<'\n';}
  iterations=it+1;if(stats[0]==0)break;
 }
 x.map=x.best_map;x.groups=x.best_groups;x.refresh_groups();x.rebuild();auto stats=x.measure();int count=x.catalog();
 std::cout<<std::setprecision(12)<<"{\"M\":"<<M<<",\"G\":"<<G<<",\"iterations\":"<<iterations<<",\"errors\":"<<stats[0]<<",\"valid_merges\":"<<stats[1]<<",\"valid_triples\":"<<stats[2]<<",\"catalog\":"<<count<<",\"seconds\":"<<elapsed()<<",\"edges\":[";
 for(int j=0;j<63;j++){int e=x.map.edge[j];if(j)std::cout<<',';if(e<0)std::cout<<"null";else std::cout<<'['<<x.edges[e].first<<','<<x.edges[e].second<<','<<x.map.color[j]<<']';}
 std::cout<<"]}\n";
}
