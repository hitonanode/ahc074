#include "saved.hpp"
#include "design.hpp"
#include <map>

int main(int argc,char**argv){
 if(argc<4)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto&s=*base;std::ifstream in(argv[3]);int own0,own1,window;in>>own0>>own1>>window;assert(window==s.handle[0]);
 std::array<std::array<float,P>,P>price;for(auto&row:price)row.fill(1e10);std::array<double,P>self{};char type;
 while(in>>type){if(type=='S'){int a;double p;in>>a>>p;self[a]=p;}else{int a,b;double p;in>>a>>b>>p;price[a][b]=price[b][a]=p;}}
 auto A=s.A;for(auto&x:A)x&=kActiveWindows;std::map<u64,int>index;for(int u=0;u<P;u++)index[A[u]]=u;
 int iterations=argc>4?std::stoi(argv[4]):20000000;std::cout<<std::setprecision(12)<<"[";
 for(int mixed=0;mixed<=1;mixed++){
  MixedDesign d(A,6,s.G);d.handle=s.handle;for(int u=0;u<P;u++)d.hb[u]=s.handle_bits(A[u]);
  if(mixed){d.own0=own0;d.own1=own1;d.single_cost=self;}
  auto compatible=[&](u64 a,u64 b){return mixed?price[index.at(a)][index.at(b)]<1e9:s.comparator.compatible(a,b);};
  auto estimate=[&](u64 a,u64 b)->double{if(mixed)return price[index.at(a)][index.at(b)];auto reach=s.comparator.closure(a,a^b);u64 key=0;for(int i=0;i<6;i++)key|=u64(reach[i])<<(8*i);return PosetSums::get().both_of(key)/1440.;};
  auto start=std::chrono::steady_clock::now();if(!d.initialize(compatible,estimate,[]{return false;})){std::cerr<<"initialize failed "<<mixed<<"\n";return 4;}
  d.anneal(1e9,iterations);d.filler_climb(1e9,65000);for(auto u:d.unit)assert(d.valid(u,u.c));
  int rescued=0;double col=0,hole=0,generic=0;for(int c=0;c<d.H;c++){col+=d.colcost(c);hole+=d.hcost(c);}for(auto u:d.unit){generic+=d.gc(u);if(u.b>=0&&!s.comparator.compatible(A[u.a],A[u.b]))rescued++;}
  // The module prices include the two owned commodities' retrieval, so the
  // constant one-step rank cost of their two singleton column is counted once.
  if(mixed)col-=1;
  std::cout<<(mixed?",":"")<<"{\"mixed\":"<<mixed<<",\"model\":"<<(col+hole+generic)/P<<",\"col\":"<<col/P<<",\"hole\":"<<hole/P<<",\"generic\":"<<generic/P<<",\"rescued\":"<<rescued<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"units\":[";
  for(int i=0;i<d.U;i++){auto u=d.unit[i];std::cout<<(i?",":"")<<"["<<u.a<<","<<u.b<<","<<u.c<<"]";}std::cout<<"],\"handles\":[";for(int c=0;c<d.H;c++)std::cout<<(c?",":"")<<d.handle[c];std::cout<<"]}"<<std::flush;
 }
 std::cout<<"]\n";
}
