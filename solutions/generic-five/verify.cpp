#define main inherited_main
#include "main.cpp"
#undef main
int main(){
 Comparator comp;std::mt19937_64 rng(779879);comp.init(5,10,rng);comp.build_tables();const auto&table=PosetSums::get();int checked=0,plans=0;
 for(unsigned s=0;s<table.kSize;s++)if(table.keys[s]!=table.kEmpty){
  u64 r=table.keys[s],target=0,holes=0;
  for(int j=0;j<10;j++){auto[a,b]=comp.edge[j];bool forward=r>>(8*a+b)&1,backward=r>>(8*b+a)&1;assert(!(forward&&backward));if(forward||backward){holes|=1ULL<<j;target|=u64(comp.polarity[j]^backward)<<j;}}
  double mean=comp.mean_moves(target,holes);assert(std::abs(mean*720-table.one[s])<1e-8);
  if(checked%64==0)for(int start=0;start<120;start++){
   auto order=comp.perms[start];auto path=comp.plan(order,target,holes);int best=255;
   for(int goal:comp.satisfying(target,holes))best=std::min(best,comp.distance(start,goal));assert(int(path.size())==best);
   for(auto[k,depth]:path){int at=std::find(order.begin(),order.end(),k)-order.begin();assert(at<4);order.erase(order.begin()+at);order.insert(order.begin()+depth,k);}
   u64 shown=0,covered=0;for(int k:order){shown|=comp.black[k]&~covered;covered|=comp.opq[k];}assert(!((shown^target)&holes));plans++;
  }
  checked++;
 }
 assert(checked==4231);std::cout<<"closed_relations = "<<checked<<"\nplans = "<<plans<<'\n';
}
