#include "saved.hpp"
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/maximum_weighted_matching.hpp>
int main(int argc,char**argv){
 if(argc<3)return 2;auto s=head::load(argv[1],argv[2]);if(!s)return 3;
 struct Edge{int a,b;long long cost;};std::vector<Edge> edges;
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
  u64 diff=(s->A[a]^s->A[b])&kActiveWindows;if(__builtin_popcountll(diff)>26||!s->comparator.compatible(s->A[a],s->A[b]))continue;
  auto r=s->comparator.closure(s->A[a],diff);u64 key=0;for(int j=0;j<6;j++)key|=u64(r[j])<<(8*j);
  long long cost=1800*__builtin_popcountll(diff&s->hmask)+5*PosetSums::get().both_of(key)+144*__builtin_popcountll(diff);
  edges.push_back({a,b,cost});
 }
 std::sort(edges.begin(),edges.end(),[](auto&a,auto&b){return std::tie(a.cost,a.a,a.b)<std::tie(b.cost,b.a,b.b);});
 std::array<bool,P> used{};long long greedy=0;int count=0;
 for(auto e:edges)if(!used[e.a]&&!used[e.b]){greedy+=e.cost;used[e.a]=used[e.b]=true;if(++count==71)break;}
 assert(count==71);
 // 114 dummy vertices each consume one unused product. A maximum-cardinality
 // matching then has exactly 71 product pairs. The common edge bonus exceeds
 // every possible total real cost, so maximum weight first makes it perfect.
 constexpr int V=370;constexpr long long bonus=100000000;
 using Graph=boost::adjacency_list<boost::vecS,boost::vecS,boost::undirectedS,boost::no_property,boost::property<boost::edge_weight_t,long long>>;
 Graph graph(V);for(auto e:edges)boost::add_edge(e.a,e.b,bonus-e.cost,graph);
 for(int d=P;d<V;d++)for(int a=0;a<P;a++)boost::add_edge(d,a,bonus,graph);
 std::vector<Graph::vertex_descriptor> mate(V);auto map=boost::make_iterator_property_map(mate.begin(),get(boost::vertex_index,graph));double start=elapsed_sec();
 boost::maximum_weighted_matching(graph,map);
 long long exact=0;int real=0;
 for(int i=0;i<V;i++){assert(mate[i]<V);assert(mate[mate[i]]==unsigned(i));if(i>=P)assert(mate[i]<P);}
 for(int i=0;i<P;i++)if(mate[i]<P&&mate[i]>unsigned(i)){
  auto[e,ok]=boost::edge(i,mate[i],graph);assert(ok);exact+=bonus-get(boost::edge_weight,graph,e);real++;
 }
 assert(real==71);assert(exact<=greedy);
 std::cout<<std::setprecision(12)<<"{\"greedy\":"<<greedy/(71.*3600)<<",\"exact\":"<<exact/(71.*3600)<<",\"difference\":"<<(exact-greedy)/(256.*3600)<<",\"edges\":"<<edges.size()<<",\"seconds\":"<<elapsed_sec()-start<<",\"pairs\":[";
 bool first=true;for(int i=0;i<P;i++)if(mate[i]<P&&mate[i]>unsigned(i)){std::cout<<(first?"":",")<<"["<<i<<","<<mate[i]<<"]";first=false;}
 std::cout<<"]}\n";
}
