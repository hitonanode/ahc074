#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;int mode=0;
 std::cout<<std::setprecision(12)<<"[";
 for(int G:{38,37,39}){
  auto a=base->A;for(auto&v:a)v&=kActiveWindows;Comparator comp;
  std::mt19937_64 init(779879);comp.init(6,G,init);
  std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);double start=elapsed_sec();
  auto stats=assign_windows(a,6,G,comp.edge,comp.polarity,permutation,1e9,250000,50000,0);comp.rebuild();
  auto d=std::make_unique<Design>(a,6,G);
  auto estimate=[&](u64 x,u64 y){auto relation=comp.closure(x,x^y);u64 r=0;for(int j=0;j<6;j++)r|=u64(relation[j])<<(8*j);return PosetSums::get().both_of(r)/1440.;};
  bool valid=d->initialize([&](u64 x,u64 y){return comp.compatible(x,y);},estimate,[]{return false;});assert(valid);
  int edges=0;for(int u=0;u<P;u++)edges+=d->partners[u].size();
  d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);d->refresh_reset();
  ProbabilityHead head(*d,2,true);double merit=(d->cur-head.rebuild())/P;
  double col=0,hole=0,gen=0;for(int c=0;c<d->H;c++)col+=d->colcost(c),hole+=d->hcost(c);for(auto u:d->unit)gen+=d->gc(u);
  Solver s=*base;s.G=G;s.H=63-G;s.gmask=low_bits(G);s.hmask=kActiveWindows&~s.gmask;s.comparator=comp;
  for(int u=0;u<P;u++)a[u]|=base->A[u]&kCapBit;s.A=a;
  for(int k=0;k<6;k++)s.paper[k]={comp.opq[k],comp.black[k]};materialize(s,*d);
  Perforation perforation(s);perforation.run(.5,1,false);perforation.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();double design_seconds=elapsed_sec()-start;long long total=0,wrong=0;std::vector<double> values;
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;long long count=0;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);count+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){
     for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
     assert(before==s.order);
    }
   }
   total+=count;values.push_back(double(count)/1024);
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(sequences*1024);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"G\":"<<G<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"model\":"<<d->cur/P<<",\"merit\":"<<merit<<",\"column\":"<<col/P<<",\"hole\":"<<hole/P<<",\"generic\":"<<gen/P<<",\"gobj\":"<<stats.gobj_after<<",\"edges\":"<<edges/2<<",\"perforation_holes\":"<<perforation.holes()<<",\"design_seconds\":"<<design_seconds<<",\"samples\":[";
  for(int i=0;i<sequences;i++)std::cout<<(i?",":"")<<values[i];std::cout<<"]}"<<std::flush;
 }
 std::cout<<"]\n";
}
