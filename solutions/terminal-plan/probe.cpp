#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);Perforation p(*base);p.run(.5,1,false);p.install();
 base->init_handle_cache();base->adaptive_initialized=false;base->init_adaptive();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 int sequences=argc>3?std::stoi(argv[3]):8;double reference=0;u64 expected=0;std::vector<int>last_lengths;
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<2;mode++){
  Solver s=*base;auto initial=s.save();long long total=0;double start=elapsed_sec();u64 hash=14819374583ULL;
  auto add=[&](u64 v){hash^=v+0x9e3779b97f4a7c15ULL+(hash<<6)+(hash>>2);};
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(3810000029ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;s.last_request=mode&&t==1023;
    auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
    if(t<1023)add(path.size());
    for(auto[k,depth]:path){if(t<1023)add(256*k+depth);int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);
    if(t<1023)for(int k:s.order)add(k);
    else if(!mode)last_lengths.push_back(path.size());else assert(path.size()<=size_t(last_lengths[q]));
   }
  }
  if(!mode)expected=hash;else assert(hash==expected);assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"saved\":"<<double(s.terminal_saved)/sequences<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
