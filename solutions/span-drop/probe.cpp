#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
#include "drop.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int sequences=argc>3?std::stoi(argv[3]):16;auto old=recover(*base);old->refresh_reset();
 double start=elapsed_sec();auto candidates=drop_candidates(*old,base->comparator);double dropsec=elapsed_sec()-start;assert(!candidates.empty());
 int chosen=std::min_element(candidates.begin(),candidates.end(),[](auto&a,auto&b){return a.merit<b.merit;})-candidates.begin();
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<3;mode++){
  auto d=mode?std::make_unique<Design>(*candidates[mode==1?0:chosen].d):std::make_unique<Design>(*old);
  auto comp=mode?candidates[mode==1?0:chosen].comp:base->comparator;
  if(mode)complete_prices(*d,comp);
  // The baseline gets the same extra search as each structural candidate.
  d->anneal(1e9,1000000);d->filler_climb(1e9,15000);rematch_probability(*d,2,1,2,true,true);d->refresh_reset();
  ProbabilityHead head(*d,2,true);double merit=(d->cur-head.rebuild())/P;
  Solver s=*base;s.G=d->G;s.H=d->H;s.gmask=low_bits(d->G);s.hmask=kActiveWindows&~s.gmask;s.comparator=comp;
  s.A=d->A;for(int u=0;u<P;u++)s.A[u]|=base->A[u]&kCapBit;
  for(int k=0;k<6;k++)s.paper[k]={comp.opq[k],comp.black[k]};materialize(s,*d);
  Perforation perforation(s);perforation.run(.5,1,false);perforation.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();long long total=0,wrong=0;std::vector<double>values;
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;long long count=0;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);count+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
   total+=count;values.push_back(double(count)/1024);
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(sequences*1024);if(!mode)reference=value;
  int candidate=mode==1?0:chosen;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"G\":"<<d->G<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"model\":"<<d->cur/P<<",\"merit\":"<<merit<<",\"drop_seconds\":"<<dropsec<<",\"window\":"<<(mode?candidates[candidate].window:-1)<<",\"position\":"<<(mode?candidates[candidate].position:-1)<<",\"moved\":"<<(mode?candidates[candidate].moved:0)<<",\"samples\":[";
  for(int i=0;i<sequences;i++)std::cout<<(i?",":"")<<values[i];std::cout<<"]}"<<std::flush;
 }
 std::cout<<"]\n";
}
