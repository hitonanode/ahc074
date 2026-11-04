#define HOLE_HELPER_NO_MAIN
#include "probe.cpp"
int main(int argc,char**argv){if(argc<3)return 2;int columns=argc>3?std::stoi(argv[3]):8;HelperModel m;if(!m.load(argv[1],argv[2],columns))return 3;auto base=m.evaluate(m.masks);std::cout<<std::setprecision(12)<<"{\"baseline\":"<<base.value<<",\"donors\":"<<m.donors.size()<<",\"columns\":"<<columns<<",\"bounds\":[";
for(int variant=0;variant<4;variant++){
 double overhead=.5+.5*variant;std::vector<std::pair<double,int>> ranked;int possible=0;
 for(int i=0;i<int(m.pairs.size());i++){
  auto&p=m.pairs[i];double fee=p.original;
  if(fee<0){double sc[2]={1e6,1e6};
   for(int side=0;side<2;side++){int u=side?p.b:p.a;for(auto&d:m.donors){u64 req=p.diff&~low_bits(m.model.G);if((d.black^m.model.A[u])&d.op&req)continue;u64 removed=(d.black^m.model.A[u])&p.residual[side];if(!m.dag(d.black,removed))continue;u64 op=d.op&~removed;if(!m.dag(m.model.A[u],p.residual[side]&~op))continue;double gen=m.mean(m.model.A[u],p.diff&~op),retrieve=.5*(d.count-1),credit=.4*__builtin_popcountll(req&op);sc[side]=std::min(sc[side],gen+retrieve+overhead-credit);}}
   fee=sc[0]+sc[1];possible+=fee<1e5;
  }
  if(fee<1e5)ranked.emplace_back(fee+.65*__builtin_popcountll(p.diff&~low_bits(m.model.G))+.04*__builtin_popcountll(p.diff),i);
 }
 std::sort(ranked.begin(),ranked.end());std::array<bool,256> used{};int count=0,novel=0;double total=0;for(auto [c,i]:ranked){auto&p=m.pairs[i];if(used[p.a]||used[p.b])continue;used[p.a]=used[p.b]=true;total+=c;novel+=p.original<0;if(++count==71)break;}
 std::cout<<(variant?",":"")<<"{\"overhead\":"<<overhead<<",\"matched\":"<<count<<",\"novel\":"<<novel<<",\"possible\":"<<possible<<",\"cost\":"<<total/256<<",\"difference\":"<<total/256-base.value<<"}";
}std::cout<<"]}\n";return 0;}
