#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto d=recover(*base);
 d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);
 materialize(*base,*d);base->init_handle_cache();Perforation p(*base);p.run(.5,1,false);p.install();
 base->adaptive_initialized=false;base->init_adaptive();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 const std::array<std::array<double,8>,8>modes{{{1,1,1,0.6,0.6,0.25,-0.25,0},{1,1,1.88091236091,0.6,0.6,0.25,-0.25,0},{1,1,1,0.91336365818,1.00003133393,0.25,-0.25,0},{1,1,1,0.6,0.6,0.80845439215,-0.854235086172,0},{1,1,1,0.6,0.6,0.25,-0.25,0.0396310623315},{1,1,1,0.6,1,0.25,-0.25,0},{1,1,1,0.9,0.6,0.25,-0.25,0},{1,1,1.44045618045,0.75668182909,0.800015666967,0.529227196075,-0.552117543086,0.0198155311658}}};
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<8;mode++){
  Solver::value_weights=modes[mode];
  Solver s=*base;s.adaptive_initialized=false;s.init_adaptive();auto initial=s.save();long long total=0,wrong=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(588331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong&&!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"seconds\":"<<elapsed_sec()-start<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
