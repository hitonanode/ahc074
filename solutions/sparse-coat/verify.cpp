#define OVERCOAT_NO_MAIN
#include "probe.cpp"
int main(){
 std::mt19937_64 rng(281000003);Comparator comp;comp.init(6,38,rng);ExactGraph graph(comp);
 int checked=0;
 for(int it=0;it<1000;it++){
  auto r=comp.closure(rng(),rng());u64 key=0;bool valid=true;
  for(int k=0;k<6;k++){valid&=!(r[k]>>k&1);key|=u64(r[k])<<(8*k);}
  if(!valid){assert(graph.one(r)<0);continue;}
  auto&t=PosetSums::get();double expected=t.one[t.slot_of(key)]/720.;assert(std::abs(expected-graph.one(r))<1e-12);checked++;
 }
 std::cout<<"complete graph exact matches = "<<checked<<"\n";
}
