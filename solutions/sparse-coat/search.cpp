#include "search.hpp"

// Keep a complete graph on sheets 0..4, and only degree windows for sheet 5.
// Moving a star window exchanges its role with an ordinary comparison window.
int main(int argc,char**argv){
 if(argc<3)return 2;
 int degree=argc>3?std::stoi(argv[3]):3,steps=argc>4?std::stoi(argv[4]):100000;
 int seed=argc>5?std::stoi(argv[5]):1;
 auto source=coat::load(argv[1],argv[2]);if(!source)return 3;
 auto q=std::make_unique<Search>(*source);q->rng.x=710000003ULL*seed;
 auto start=std::chrono::steady_clock::now();auto baseline=q->evaluate();
 std::vector<std::pair<int,int>> ordinary;
 for(int a=0;a<5;a++)for(int b=a+1;b<5;b++)ordinary.emplace_back(a,b);
 std::vector<int>star;
 for(int j=0;j<q->comp.G;j++)if(q->comp.edge[j].second==5)star.push_back(j);
 for(int j=int(star.size())-1;j>0;j--)std::swap(star[j],star[q->rng.mod(j+1)]);
 if(degree>int(star.size()))return 4;
 for(int i=0;i<int(star.size());i++){
  int j=star[i];q->comp.edge[j]=i<degree?std::pair<int,int>{i,5}:ordinary[q->rng.mod(ordinary.size())];
 }
 auto cur=q->evaluate(),initial=cur,best=cur;
 auto be=q->comp.edge;auto bp=q->comp.polarity;
 std::array<std::array<int,6>,6> count{};
 for(auto[a,b]:q->comp.edge)count[a][b]++;
 auto remember=[&]{if(cur.value<best.value){best=cur;be=q->comp.edge;bp=q->comp.polarity;}};
 for(int t=0;t<steps;t++){
  double temp=.05*std::pow(.002,double(t)/steps);
  int j=q->rng.mod(source->G),kind=q->rng.mod(8);
  if(kind==0){
   auto saved=q->comp.polarity;int b=q->rng.mod(P);if(!(source->A[b]&kCapBit))continue;
   for(int k=0;k<source->G;k++)if(q->comp.edge[k].second==5)q->comp.polarity[k]=int(source->A[b]>>k&1)^1;
   auto v=q->evaluate();if(v.value<cur.value||q->rng.real()<std::exp((cur.value-v.value)/temp))cur=v;else q->comp.polarity=std::move(saved);
   remember();continue;
  }
  if(kind<=2){
   int k=q->rng.mod(source->G);if(j==k)continue;
   std::swap(q->comp.edge[j],q->comp.edge[k]);bool pol=q->rng.mod(2);if(pol)std::swap(q->comp.polarity[j],q->comp.polarity[k]);
   auto v=q->evaluate();if(v.value<cur.value||q->rng.real()<std::exp((cur.value-v.value)/temp))cur=v;
   else{std::swap(q->comp.edge[j],q->comp.edge[k]);if(pol)std::swap(q->comp.polarity[j],q->comp.polarity[k]);}
   remember();continue;
  }
  auto old=q->comp.edge[j],next=old;int pol=q->comp.polarity[j],np=pol;
  if(kind<=4)np^=1;
  else if(old.second==5){
   next={q->rng.mod(5),5};if(next!=old&&count[next.first][5])continue;np=q->rng.mod(2);
  }else{
   if(count[old.first][old.second]<=1)continue;
   next=ordinary[q->rng.mod(ordinary.size())];np=q->rng.mod(2);
  }
  if(next==old&&np==pol)continue;
  q->comp.edge[j]=next;q->comp.polarity[j]=np;auto v=q->evaluate();
  if(v.value<cur.value||q->rng.real()<std::exp((cur.value-v.value)/temp)){
   count[old.first][old.second]--;count[next.first][next.second]++;cur=v;
  }else q->comp.edge[j]=old,q->comp.polarity[j]=pol;
  remember();
 }
 q->comp.edge=be;q->comp.polarity=bp;best=q->evaluate();
 std::cout<<std::setprecision(12)<<"{\"degree\":"<<degree<<",\"baseline\":"<<baseline.value<<",\"initial\":"<<initial.value<<",\"best\":"<<best.value<<",\"special\":"<<best.special<<",\"novel\":"<<best.novel<<",\"anchors\":"<<best.anchors<<",\"iterations\":"<<steps<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"gates\":[";
 for(int j=0;j<source->G;j++)std::cout<<(j?",":"")<<"["<<be[j].first<<","<<be[j].second<<","<<bp[j]<<"]";
 std::cout<<"]}\n";
}
