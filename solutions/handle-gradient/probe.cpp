#include "common.hpp"
#include "marginal.hpp"
#include "gradient.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);Perforation p(*base);p.run(.5,1,false);p.install();
 base->adaptive_initialized=false;base->init_adaptive();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 HandleMarginal marginal(*base);double start=elapsed_sec();auto gradient=head_gradient(*base);double gradient_seconds=elapsed_sec()-start;
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<6;mode++){
  Solver s=*base;double weight=mode==2?.125:mode==3?.25:mode==4?.5:1;
  for(int c=0;c<s.H;c++){
   double old=s.adaptive_holes[c][0]-s.adaptive_holes[c][1];
   double delta=mode==0?0:mode==1?.5*(marginal.gradient[c]-old):-weight*gradient[c];
   s.adaptive_holes[c][0]=std::max(.001,s.adaptive_holes[c][0]+.5*delta);s.adaptive_holes[c][1]=std::max(.001,s.adaptive_holes[c][1]-.5*delta);
  }
  auto initial=s.save();long long total=0,wrong=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"setup_seconds\":"<<gradient_seconds<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
