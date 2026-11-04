#include "features.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto d=recover(*base);
 d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);
 materialize(*base,*d);base->init_handle_cache();Perforation p(*base);p.run(.5,1,false);p.install();
 base->adaptive_initialized=false;base->init_adaptive();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 const std::array<double,8>original{1,1,1,.6,.6,.25,-.25,0};
 const std::array<double,11>learned{1,1,2.4610910849135,0.60114143272033,0.78733997640375,0.54857713847302,-0.098500176293317,0.015020670079845,6.181341916717,-0.34095202300855,0.98665887620197};
 const std::array<double,9>old{1,1,2.3329435839767,0.5895510043246,0.78233416199336,0.63878237701892,0.048524259909509,0.020579913137339,10.05971918645};
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  double blend=std::array<double,4>{0,.5,1,.5}[mode];
  Solver::return_deficit_weight=blend*(mode==3?old[8]:learned[8]);
  Solver::returned_weights=mode==3?std::array<double,2>{0,0}:std::array<double,2>{blend*learned[9],blend*learned[10]};
  for(int j=0;j<8;j++)Solver::value_weights[j]=original[j]+blend*((mode==3?old[j]:learned[j])-original[j]);
  Solver s=*base;s.adaptive_initialized=false;s.init_adaptive();auto initial=s.save();long long total=0,wrong=0;double start=elapsed_sec();
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(7118831000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0&&t%128==0){std::array<bool,K>extra{};if(s.top_d>=0)extra[s.top_d]=true;for(auto f:s.fillers)extra[f.paper]=true;
      auto delta=s.returned_delta(extra);Solver ref=s;for(auto&v:ref.adaptive_holes)for(auto&x:v)x/=Solver::value_weights[2];std::array<int,K>frequency{};for(int a=0;a<P;a++)frequency[ref.ded[a]]++;auto f=features(ref,frequency);assert(std::abs(f[9]-delta[0])<1e-9&&std::abs(f[10]-delta[1])<1e-9);}
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong&&!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"seconds\":"<<elapsed_sec()-start<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
