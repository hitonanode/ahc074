#define OVERCOAT_NO_MAIN
#include "probe.cpp"

int main(int argc,char**argv){
 if(argc<3)return 2;
 auto s=coat::load(argv[1],argv[2]);if(!s)return 3;
 if(argc>3&&std::string(argv[3])!="-"){
  std::ifstream map(argv[3]);int g;map>>g;if(g!=s->G)return 4;
  for(int j=0;j<g;j++)map>>s->comparator.edge[j].first>>s->comparator.edge[j].second>>s->comparator.polarity[j];
  if(!map)return 5;
  s->comparator.rebuild();
 }
 for(int k=0;k<6;k++)s->paper[k]={s->comparator.opq[k],s->comparator.black[k]};
 int iterations=argc>4?std::stoi(argv[4]):20000000;
 auto start=std::chrono::steady_clock::now();
 auto exp=std::make_unique<Experiment>(*s);exp->graph=std::make_unique<ExactGraph>(s->comparator);exp->tables();
 std::unordered_map<u64,int>index;for(int a=0;a<P;a++)index[exp->A[a]]=a;
 auto d=std::make_unique<Design>(exp->A,6,s->G);
 bool ok=d->initialize([&](u64 a,u64 b){return exp->costs[index.at(a)][index.at(b)].cost>=0;},[&](u64 a,u64 b){return exp->costs[index.at(a)][index.at(b)].cost;},[]{return false;});
 if(!ok){std::cout<<"{\"valid\":false}\n";return 0;}
 d->anneal(1e9,iterations);
 int special=0,novel=0;double generic=0;
 for(auto u:d->unit)if(u.b>=0){special+=exp->costs[u.a][u.b].row>=0;novel+=!s->comparator.compatible(exp->A[u.a],exp->A[u.b]);generic+=d->gc(u);}
 std::cout<<std::setprecision(12)<<"{\"valid\":true,\"model\":"<<d->cur/P<<",\"generic\":"<<generic/P<<",\"special\":"<<special<<",\"novel\":"<<novel<<",\"anchors\":"<<exp->anchors.size()<<",\"priced\":"<<exp->graph->cache.size()<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
