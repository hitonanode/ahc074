#define FREE_CODE_NO_MAIN
#include "base.hpp"
#include <iomanip>
int main(int argc,char**argv){if(argc<3)return 2;int iterations=argc>3?std::stoi(argv[3]):3000;double initial_temperature=argc>4?std::stod(argv[4]):.3;u64 seed=argc>5?std::stoull(argv[5]):1;
 int random_start=argc>6?std::stoi(argv[6]):0,acceptance=argc>7?std::stoi(argv[7]):0;
 auto q=std::make_unique<free_code::Search>(seed);if(!q->load(argv[1],argv[2]))return 3;auto clock_start=std::chrono::steady_clock::now();auto base=q->matching(0,true);auto exact_base=q->exact();auto best=base;auto best_state=q->state;int best_step=-1,nonlinear=0,feasible=0,accepted=0;
 if(random_start){auto d=q->state;for(auto&g:d)g=q->rng.mod(q->gates.size());q->reset(d);}
 std::vector<int> selected,states,targets;std::vector<std::array<u64,3>> truth(q->gates.size());std::array<std::array<u64,3>,64>needs{},wanted{};
 // Sampling is done after subtracting the least error, so no underflow can
 // discard every candidate. The latent orders are resampled even at ties.
 auto choose=[&](const std::vector<int>&error,double temperature){int mn=*std::min_element(error.begin(),error.end());std::vector<double>weight(error.size());double sum=0;for(int i=0;i<int(error.size());i++)sum+=weight[i]=std::exp((mn-error[i])/temperature);double r=q->rng.real()*sum;for(int i=0;i<int(error.size());i++)if((r-=weight[i])<=0)return i;return int(error.size())-1;};
 for(int it=0;it<iterations;it++){
  double progress=double(it)/iterations;double temperature=initial_temperature*std::pow(.04,progress);double lambda=4+4*progress;
  auto old_design=q->state;double old_value=acceptance?q->matching(lambda,false).value:0;
  if(it%5==0||selected.empty())selected=q->matching(4+4*progress,false).selected;
  if(selected.size()!=71){selected=q->matching(2,false).selected;if(selected.size()!=71)return 4;}
  states.clear();targets.clear();for(auto&x:needs)x.fill(0);for(auto&x:wanted)x.fill(0);
  for(int id:selected){auto&p=q->pairs[id];for(int side=0;side<2;side++){
   std::vector<int>error(720);for(int s=0;s<720;s++)error[s]=side?p.n-q->mismatch[id*720+s]:q->mismatch[id*720+s];int state=choose(error,temperature),index=states.size();states.push_back(state);int target=side?p.b:p.a;targets.push_back(target);
   for(u64 z=p.diff;z;z&=z-1){int j=__builtin_ctzll(z);needs[j][index>>6]|=1ULL<<(index&63);if(q->products[target]>>j&1)wanted[j][index>>6]|=1ULL<<(index&63);}
  }}
  for(int g=0;g<int(q->gates.size());g++){truth[g].fill(0);for(int z=0;z<int(states.size());z++)if(q->gates[g].truth[states[z]])truth[g][z>>6]|=1ULL<<(z&63);}
  auto design=q->state;std::vector<int>error(q->gates.size());
  for(int j=0;j<q->G;j++){
   for(int g=0;g<int(q->gates.size());g++){error[g]=0;for(int w=0;w<3;w++)error[g]+=__builtin_popcountll((truth[g][w]^wanted[j][w])&needs[j][w]);}
   design[j]=choose(error,temperature);
  }
  q->reset(design);
  auto candidate=q->matching(0,true);if(candidate.selected.size()==71)feasible++;
  if(candidate.value<best.value){best=candidate;best_state=q->state;best_step=it;std::cerr<<"best "<<it<<" value "<<best.value<<" temp "<<temperature<<'\n';}
  if(acceptance){double new_value=q->matching(lambda,false).value,at=.06*std::pow(.01,progress);if(new_value<=old_value||q->rng.real()<std::exp((old_value-new_value)/at))accepted++;else q->reset(old_design);}
  if(it%200==0)std::cerr<<"step "<<it<<" hard "<<candidate.value<<" best "<<best.value<<" feasible "<<feasible<<'\n';
 }
 int last_nonlinear=0;for(int g:q->state)last_nonlinear+=__builtin_popcount(q->gates[g].opaque)!=2;auto last_exact=q->exact();q->reset(best_state);auto exact=q->exact();for(int g:best_state)nonlinear+=__builtin_popcount(q->gates[g].opaque)!=2;
 std::cout<<std::setprecision(12)<<"{\"baseline_proxy\":"<<base.value<<",\"best_proxy\":"<<best.value<<",\"baseline_exact\":"<<exact_base.value<<",\"best_exact\":"<<exact.value<<",\"difference\":"<<exact.value-exact_base.value<<",\"nonlinear\":"<<nonlinear<<",\"last_nonlinear\":"<<last_nonlinear<<",\"last_exact\":"<<last_exact.value<<",\"matched\":"<<exact.matched<<",\"available\":"<<exact.available<<",\"feasible_iterations\":"<<feasible<<",\"best_step\":"<<best_step<<",\"iterations\":"<<iterations<<",\"temperature\":"<<initial_temperature<<",\"rng_seed\":"<<seed<<",\"random_start\":"<<random_start<<",\"acceptance\":"<<acceptance<<",\"accepted\":"<<accepted<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-clock_start).count()<<",\"gates\":[";
 for(int j=0;j<q->G;j++){auto g=q->gates[best_state[j]];std::cout<<(j?",":"")<<"["<<g.opaque<<","<<g.black<<"]";}std::cout<<"]}\n";
}
