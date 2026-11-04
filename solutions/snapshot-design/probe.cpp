#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
struct Swap {int x=-1,y=-1;double predicted=0;long long n=0;double sum=0,square=0,raw=0;};
void replace_units(Design&d,int x,int y){
 auto a=d.unit[x],b=d.unit[y],na=b,nb=a;na.c=a.c;nb.c=b.c;
 d.update(a,-1);d.update(b,-1);d.update(na,1);d.update(nb,1);d.unit[x]=na;d.unit[y]=nb;
 d.owner[na.a]=x;if(na.b>=0)d.owner[na.b]=x;d.owner[nb.a]=y;if(nb.b>=0)d.owner[nb.b]=y;
}
std::vector<Swap> proposals(Design&d,int count){
 ProbabilityHead head(d,2,true);auto gradient=head.probability_gradient();std::vector<Swap>all;
 for(int x=0;x<d.U;x++)for(int y=x+1;y<d.U;y++){
  auto a=d.unit[x],b=d.unit[y],na=b,nb=a;na.c=a.c;nb.c=b.c;
  if(a.c==b.c||d.weight(a)!=d.weight(b)||!d.valid(na,na.c)||!d.valid(nb,nb.c)||d.color(a,a.c)!=d.color(na,na.c)||d.color(b,b.c)!=d.color(nb,nb.c))continue;
  double gain=0;
  for(int u:{a.a,a.b})if(u>=0)gain+=head.target(u,nb)-head.target(u,a);
  for(int u:{b.a,b.b})if(u>=0)gain+=head.target(u,na)-head.target(u,b);
  if(head.beta[x])gain+=head.beta[x]*(head.donor(na)-head.utility[x]);
  if(head.beta[y])gain+=head.beta[y]*(head.donor(nb)-head.utility[y]);
  double before=d.cur;replace_units(d,x,y);
  for(int c=0;c<d.H;c++){
   double z=d.hn[c][0],o=d.hn[c][1],t=2.*d.nt[c],den=z+o+t;
   double probability=den?(o+t*(o>z))/den:.5;
   gain+=gradient[c]*(probability-head.prob[c][1]);
  }
  all.push_back({x,y,(d.cur-before-gain)/P});replace_units(d,x,y);d.cur=before;
 }
 d.rebuild();std::sort(all.begin(),all.end(),[](auto&a,auto&b){return a.predicted<b.predicted;});
 if(int(all.size())>count)all.resize(count);return all;
}
struct Sample{Solver::State state;int u;u64 shown;double cost;int moves;};
double potential(const Solver&s){return s.filler_charge()+s.adaptive_next_cost();}
void rebuild_solver(Solver&s,const Design&d,bool perforated){
 materialize(s,d);s.init_handle_cache();
 if(perforated){Perforation p(s);p.run(.5,1,false);p.install();s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();}
}
std::vector<Sample> snapshots(Solver s,int n){
 std::vector<Sample>data;data.reserve(n);std::mt19937_64 rng(93810000003ULL);int prev=rng()%P;
 for(int t=0;t<n+512;t++){
  int u=rng()%(P-1);if(u>=prev)u++;prev=u;
  Sample sample{s.save(),u,s.display(),potential(s),0};
  auto path=s.process(u);assert(s.display()==s.A[u]);sample.moves=path.size();sample.cost=sample.moves+potential(s)-sample.cost;
  if(t>=512)data.push_back(std::move(sample));
 }
 assert(!s.plan_failures);return data;
}
void evaluate_swap(Swap&swap,const Solver&base,const Design&original,const std::vector<Sample>&data,int from,int to){
 auto d=original;replace_units(d,swap.x,swap.y);d.rebuild();Solver s=base;rebuild_solver(s,d,false);
 int x=swap.x+7,y=swap.y+7;
 for(int i=from;i<to;i++){
  const auto&sample=data[i];bool outside=sample.state.top_d==x||sample.state.top_d==y;
  for(auto f:sample.state.fillers)outside|=f.paper==x||f.paper==y;if(outside)continue;
  s.restore(sample.state);if(s.display()!=sample.shown)continue;
  double before=potential(s);auto path=s.process(sample.u);assert(s.display()==s.A[sample.u]);
  double delta=path.size()+potential(s)-before-sample.cost;
  swap.n++;swap.sum+=delta;swap.square+=delta*delta;swap.raw+=int(path.size())-sample.moves;
 }
 assert(!s.plan_failures);
}
double holdout(Solver s,int sequences){
 auto initial=s.save();long long total=0;
 for(int q=0;q<sequences;q++){
  s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
  for(int t=0;t<1024;t++){
   int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
   if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
  }
 }
 assert(!s.plan_failures);return double(total)/(sequences*1024);
}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int sequences=argc>3?std::stoi(argv[3]):16,maximum=argc>4?std::stoi(argv[4]):32768;
 auto original=recover(*base);original->refresh_reset();rebuild_solver(*base,*original,false);
 double start=elapsed_sec();auto swaps=proposals(*original,128);std::cerr<<"proposals = "<<swaps.size()<<"\n";
 auto data=snapshots(*base,maximum);std::cerr<<"snapshots = "<<data.size()<<"\n";
 std::vector<int>active(swaps.size());std::iota(active.begin(),active.end(),0);int previous=0;
 for(int end:{std::min(1024,maximum),std::min(8192,maximum),maximum}){
  if(end<=previous)continue;
  for(int id:active)evaluate_swap(swaps[id],*base,*original,data,previous,end);
  std::sort(active.begin(),active.end(),[&](int a,int b){return swaps[a].sum/std::max(1LL,swaps[a].n)<swaps[b].sum/std::max(1LL,swaps[b].n);});
  int keep=end<=1024?16:end<=8192?4:4;if(int(active.size())>keep)active.resize(keep);
  previous=end;std::cerr<<"stage = "<<end<<" best = "<<(active.empty()?0:swaps[active[0]].sum/swaps[active[0]].n)<<"\n";
 }
 double train_seconds=elapsed_sec()-start;
 int best=-1,best_raw=-1,best_safe=-1;double score=0,raw=0,safe=0;
 for(int id:active){auto&v=swaps[id];double mean=v.sum/v.n,r=v.raw/v.n,se=std::sqrt(std::max(0.,v.square/v.n-mean*mean)/std::max(1LL,v.n-1));
  if(mean<score)score=mean,best=id;if(r<raw)raw=r,best_raw=id;if(mean+2*se<safe)safe=mean+2*se,best_safe=id;
 }
 std::cout<<std::setprecision(12)<<"{\"train_seconds\":"<<train_seconds<<",\"proposals\":"<<swaps.size()<<",\"samples\":"<<maximum<<",\"finalists\":[";
 bool first=true;for(int id:active){auto&v=swaps[id];std::cout<<(first?"":",")<<"{\"id\":"<<id<<",\"x\":"<<v.x<<",\"y\":"<<v.y<<",\"predicted\":"<<v.predicted<<",\"n\":"<<v.n<<",\"cv\":"<<v.sum/v.n<<",\"raw\":"<<v.raw/v.n<<"}";first=false;}
 std::cout<<"],\"results\":[";double reference=0;int mode=0;
 for(int id:{-1,best,best_raw,best_safe}){
  auto d=*original;if(id>=0)replace_units(d,swaps[id].x,swaps[id].y);d.rebuild();Solver s=*base;rebuild_solver(s,d,true);
  double value=holdout(s,sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"choice\":"<<id<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<"}"<<std::flush;
 }
 std::cout<<"]}\n";
}
