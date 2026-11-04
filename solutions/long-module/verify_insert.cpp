#define main research_main
#include "model.cpp"
#undef main
int main(int argc,char**argv){if(argc<2)return 2;Model m(argv[1],8);std::mt19937_64 rng(94263);int compared=0;
for(int test=0;test<1000;test++){
 State s(m.K);std::iota(s.begin(),s.end(),0);std::shuffle(s.begin(),s.end(),rng);int k=s.back();s.pop_back();if(test&1)s.pop_back();auto costs=m.insertion_values(s,k);
 for(int d=0;d<=int(s.size());d++){State t=s;t.insert(t.begin()+d,k);double slow=m.value(t);if(costs[d]!=slow){std::cerr<<test<<' '<<d<<' '<<costs[d]<<' '<<slow<<'\n';return 3;}compared++;}
 std::vector<Node>a,b;m.expand(s,a);m.expand_slow(s,b);if(a.size()!=b.size())return 4;for(int j=0;j<int(a.size());j++)if(a[j].order!=b[j].order||a[j].value!=b[j].value)return 5;
}
 m.fast_insert=false;double slow=m.simulate(4096,57383);m.fast_insert=true;double fast=m.simulate(4096,57383);assert(slow==fast);
std::cout<<compared<<" insertion prices and 1000 expanded state sets match; 4096-query simulation "<<fast<<" equals slow\n";return 0;}
