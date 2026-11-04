#include "design.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int iterations=argc>3?std::stoi(argv[3]):10000000;
 double reference=0;int mode=0;std::cout<<std::setprecision(12)<<"[";
 for(int G:{38,18,22,26,30,34}){
  auto a=base->A;for(auto&x:a)x&=kActiveWindows;Comparator comp=base->comparator;std::unique_ptr<Design>d;
  double start=elapsed_sec();
  if(G==38)d=recover(*base);
  else{
   std::mt19937_64 rng(779879);comp.init(6,G,rng);std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);
   assign_windows(a,6,G,comp.edge,comp.polarity,permutation,1e9,250000,50000,0);comp.rebuild();assert(comp.complete);
   d=std::make_unique<Design>(a,6,G);
   auto estimate=[&](u64 x,u64 y){auto reach=comp.closure(x,x^y);u64 key=0;for(int k=0;k<6;k++)key|=u64(reach[k])<<(8*k);return PosetSums::get().both_of(key)/1440.;};
   bool valid=d->initialize([&](u64 x,u64 y){return comp.compatible(x,y);},estimate,[]{return false;});assert(valid);
  }
  for(int initial:{0,20}){
   Problem problem(*d,comp,initial!=0);Search search(problem);
   if(G==38&&initial==0){for(int c=0;c<d->H;c++)search.handles[c]=d->handle[c];for(auto u:d->unit){int id=search.lookup({u.a,u.b,-1},u.b>=0?2:1);assert(id>=0);search.units.push_back({id,u.c});}search.rebuild();}
   else if(!search.initialize(initial)){std::cerr<<"initialization failed G="<<G<<" initial="<<initial<<"\n";continue;}
   search.refresh();search.optimize(iterations);search.refresh();
   double cols=0,holes=0,generic=0;int triples=0,pairs=0;std::array<int,256>owners{};
   for(int c=0;c<search.H;c++){cols+=Search::colcost(search.counts[c]);holes+=search.holecost(c);}
   for(auto u:search.units){auto&v=search.groups[u.group];assert(search.valid(u.group,u.column));for(int j=0;j<v.n;j++)owners[v.a[j]]++;generic+=v.fee;triples+=v.n==3;pairs+=v.n==2;}
   for(int x:owners)assert(x==1);assert(std::abs(cols+holes+generic-search.current)<1e-5);
   double value=search.current/256;if(!mode)reference=value;
   std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"G\":"<<G<<",\"initial\":"<<initial<<",\"model\":"<<value<<",\"difference\":"<<value-reference<<",\"columns\":"<<cols/256<<",\"holes\":"<<holes/256<<",\"generic\":"<<generic/256<<",\"triples\":"<<triples<<",\"pairs\":"<<pairs<<",\"catalog\":"<<search.triples.size()<<",\"seconds\":"<<elapsed_sec()-start<<"}"<<std::flush;
  }
 }
 std::cout<<"]\n";
}
