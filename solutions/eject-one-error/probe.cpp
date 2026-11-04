#include "saved.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 base->init_handle_cache();base->adaptive_initialized=false;base->init_adaptive();base->comparator.build_tables();
 base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 int sequences=argc>3?std::stoi(argv[3]):8;std::string name(argv[1]);int seed=std::stoi(name.substr(name.size()-8,4));
 std::array<double,4> times{},values{},accepts{},trials{};
 for(int step=0;step<4;step++){
  int mode=(step+seed)%4;Solver::min_eject_errors=mode?1:2;Solver::one_error_filter=std::max(0,mode-1);
  Solver s=*base;auto initial=s.save();long long total=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!s.plan_failures);times[mode]=(elapsed_sec()-start)/sequences;values[mode]=double(total)/(1024*sequences);accepts[mode]=double(s.mid_accepts)/sequences;trials[mode]=double(s.mid_trials)/sequences;
 }
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++)std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<values[mode]<<",\"difference\":"<<values[mode]-values[0]<<",\"seconds\":"<<times[mode]<<",\"accepts\":"<<accepts[mode]<<",\"trials\":"<<trials[mode]<<"}";
 std::cout<<"]\n";
}
