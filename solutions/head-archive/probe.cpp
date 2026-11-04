#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto a=base->A;for(auto&x:a)x&=kActiveWindows;auto initial=std::make_unique<Design>(a,6,base->G);
 auto estimate=[&](u64 x,u64 y){auto r=base->comparator.closure(x,x^y);u64 key=0;for(int j=0;j<6;j++)key|=u64(r[j])<<(8*j);return PosetSums::get().both_of(key)/1440.;};
 assert(initial->initialize([&](u64 x,u64 y){return base->comparator.compatible(x,y);},estimate,[]{return false;}));
 initial->anneal(1e9,20000000);assert(initial->archives.size()==8);
 int sequences=argc>3?std::stoi(argv[3]):8;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<3;mode++){
  double start=elapsed_sec(),best=1e100;int chosen=-1;std::unique_ptr<Design> selected;
  for(int i=mode?0:7;i<8;i++){
   auto d=std::make_unique<Design>(*initial);d->unit=initial->archives[i].units;d->handle=initial->archives[i].handles;
   for(int u=0;u<P;u++){d->hb[u]=0;for(int c=0;c<d->H;c++)d->hb[u]|=(d->A[u]>>d->handle[c]&1)<<c;}
   d->rebuild();d->refresh_reset();
   if(mode==2)d->filler_climb(1e9,6000);
   ProbabilityHead h(*d,2,true);double merit=d->cur-h.rebuild();
   if(merit<best){chosen=i;best=merit;selected=std::move(d);}
  }
  auto&d=*selected;d.filler_climb(1e9,mode==2?59000:65000);rematch_probability(d,4,1,2,true,true);
  Solver s=*base;s.handle_cache_ready=false;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();s.adaptive_initialized=false;s.init_adaptive();
  s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();double prepare=elapsed_sec()-start;
  auto state=s.save();long long total=0;start=elapsed_sec();
  for(int q=0;q<sequences;q++){s.restore(state);std::mt19937_64 rng(885511000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"chosen\":"<<chosen<<",\"merit\":"<<best/P<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"prepare_seconds\":"<<prepare<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
