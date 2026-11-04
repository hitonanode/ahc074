#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);Perforation p(*base);p.run(.5,1,false);p.install();
 base->init_handle_cache();base->adaptive_initialized=false;base->init_adaptive();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 int sequences=argc>3?std::stoi(argv[3]):4;std::string name(argv[1]);int seed=std::stoi(name.substr(name.size()-8,4));
 std::array<double,2> time{},value{};u64 expected=0;
 for(int step=0;step<2;step++){
  int mode=(step+seed)%2;Solver::fixed_lists=mode;
  Solver s=*base;auto initial=s.save();long long total=0;u64 hash=157991994151ULL;
  auto add=[&](u64 v){hash^=v+0x9e3779b97f4a7c15ULL+(hash<<6)+(hash>>2);};double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
    add(path.size());for(auto[k,depth]:path){add(256*k+depth);int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);
    for(int k:s.order)add(k);
   }
  }
  assert(!s.plan_failures);time[mode]=(elapsed_sec()-start)/sequences;value[mode]=double(total)/(1024*sequences);
  if(!step)expected=hash;else assert(hash==expected);
 }
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<2;mode++)std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value[mode]<<",\"difference\":"<<value[mode]-value[0]<<",\"seconds\":"<<time[mode]<<"}";
 std::cout<<"]\n";
}
