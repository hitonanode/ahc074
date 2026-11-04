#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto a=base->A;for(auto&x:a)x&=kActiveWindows;auto initial=std::make_unique<Design>(a,6,base->G);
 auto estimate=[&](u64 x,u64 y){auto r=base->comparator.closure(x,x^y);u64 key=0;for(int j=0;j<6;j++)key|=u64(r[j])<<(8*j);return PosetSums::get().both_of(key)/1440.;};
 assert(initial->initialize([&](u64 x,u64 y){return base->comparator.compatible(x,y);},estimate,[]{return false;}));
 int sequences=argc>3?std::stoi(argv[3]):8,mode=0;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int count:{1,2,4}){
  std::vector<std::unique_ptr<Design>>designs;std::vector<double>raw,merit;double start=elapsed_sec();
  for(int k=0;k<count;k++){auto d=std::make_unique<Design>(*initial);d->rng.x^=0x7c317d9b51ULL*k;d->anneal(1e9,20000000/count);d->refresh_reset();if(count>1)d->filler_climb(1e9,8000);raw.push_back(d->cur/P);ProbabilityHead head(*d,2,true);merit.push_back((d->cur-head.rebuild())/P);designs.push_back(std::move(d));}
  double pool_seconds=elapsed_sec()-start;std::vector<double>scores(count,-1),refine_seconds(count),request_seconds(count);
  for(int selector=0;selector<(count==1?1:2);selector++){
   const auto&values=selector?merit:raw;int chosen=std::min_element(values.begin(),values.end())-values.begin();
   if(scores[chosen]<0){auto d=*designs[chosen];double t=elapsed_sec();d.filler_climb(1e9,count==1?65000:57000);rematch_probability(d,4,1,2,true,true);
    Solver s=*base;s.handle_cache_ready=false;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();s.adaptive_initialized=false;s.init_adaptive();
    s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();refine_seconds[chosen]=elapsed_sec()-t;
    auto state=s.save();long long total=0;t=elapsed_sec();
    for(int q=0;q<sequences;q++){s.restore(state);std::mt19937_64 rng(995511000003ULL*(q+1));int prev=rng()%P;
     for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
      if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
     }
    }
    assert(!s.plan_failures);scores[chosen]=double(total)/(1024*sequences);request_seconds[chosen]=(elapsed_sec()-t)/sequences;
   }
   if(!mode)reference=scores[chosen];std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"count\":"<<count<<",\"selector\":"<<selector<<",\"chosen\":"<<chosen<<",\"moves\":"<<scores[chosen]<<",\"difference\":"<<scores[chosen]-reference<<",\"pool_seconds\":"<<pool_seconds<<",\"refine_seconds\":"<<refine_seconds[chosen]<<",\"seconds\":"<<request_seconds[chosen]<<"}"<<std::flush;
  }
 }
 std::cout<<"]\n";
}
