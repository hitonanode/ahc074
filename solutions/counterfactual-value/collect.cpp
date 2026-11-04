#include "features.hpp"
double value(const Solver&s){return s.adaptive_next_cost()+s.filler_charge();}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto d=recover(*base);
 d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);
 materialize(*base,*d);base->init_handle_cache();Perforation p(*base);p.run(.5,1,false);p.install();base->adaptive_initialized=false;base->init_adaptive();
 base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 Solver&s=*base;std::array<int,K>frequency{};for(int u=0;u<P;u++)frequency[s.ded[u]]++;
 std::mt19937_64 rng(71883310000003ULL);int prev=rng()%P;std::cout<<std::setprecision(16)<<"[";int samples=0;
 for(int t=0;t<1024;t++){
  int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
  auto initial=s.save();s.trace_value=t>=64&&t%8==0;auto path=s.process(u);s.trace_value=false;assert(s.display()==s.A[u]);
  if(t<64||t%8)continue;
  auto chosen=s.save();auto f0=features(s,frequency);double chosen_cost=path.size()+value(s);auto raw=std::move(s.value_candidates);s.value_candidates.clear();
  std::sort(raw.begin(),raw.end(),[](const auto&a,const auto&b){return a.cost<b.cost;});
  std::vector<Solver::State>alternates;std::vector<Features>xf;
  for(auto&candidate:raw){
   if(candidate.cost>chosen_cost+1.5)continue;s.restore(candidate.state);s.canonicalize();
   auto refined=s.post_optimize(initial,std::move(candidate.path),u);refined=s.post_optimize(initial,std::move(refined),u,true);
   bool duplicate=s.order==chosen.order;for(const auto&v:alternates)duplicate|=s.order==v.order;if(duplicate)continue;
   assert(s.display()==s.A[u]&&s.fillers_reachable());alternates.push_back(s.save());auto f=features(s,frequency);for(int i=0;i<F;i++)f[i]-=f0[i];xf.push_back(f);if(alternates.size()==2)break;
  }
  s.restore(chosen);if(alternates.empty())continue;Solver trial=s;trial.value_candidates.clear();
  std::array<std::array<int,16>,8>queries;for(int q=0;q<8;q++){
   std::mt19937_64 future(668851331ULL*(1+t)*17+q);int last=u;
   for(int&x:queries[q]){x=future()%(P-1);if(x>=last)x++;last=x;}
  }
  std::array<double,8>reference{};
  auto rollout=[&](const Solver::State&st,int q){
   trial.restore(st);double total=0;
   for(int target:queries[q]){auto before=trial.order;auto path=trial.process(target);total+=path.size();assert(trial.display()==trial.A[target]);
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=trial.paper[before[j]].opaque;assert(trial.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==trial.order);}
   }return total+value(trial);
  };
  for(int q=0;q<8;q++)reference[q]=rollout(chosen,q);
  for(int a=0;a<int(alternates.size());a++){
   double target=0,square=0;for(int q=0;q<8;q++){double delta=rollout(alternates[a],q)-reference[q];target+=delta;square+=delta*delta;}
   std::cout<<(samples++?",":"")<<"{\"request\":"<<t<<",\"x\":[";for(int i=0;i<F;i++)std::cout<<(i?",":"")<<xf[a][i];std::cout<<"],\"target\":"<<target/8<<",\"variance\":"<<(square-target*target/8)/7<<"}"<<std::flush;
  }
  assert(!trial.plan_failures);s.restore(chosen);
 }
 assert(!s.plan_failures);std::cout<<"]\n";
}
