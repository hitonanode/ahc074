#include "common.hpp"
#include "search.hpp"

int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);d->refresh_reset();materialize(*base,*d);
 double begin=elapsed_sec();WeaveSearch search(*base,*d);auto choice=search.search();double seconds=elapsed_sec()-begin;
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 std::cout<<std::setprecision(12)<<"{\"near\":"<<search.near<<",\"rescued\":"<<search.rescued<<",\"replacements\":"<<search.replacements<<",\"model\":"<<(choice.x>=0?choice.delta/P:0)<<",\"design_seconds\":"<<seconds<<",\"x\":"<<choice.x<<",\"a\":"<<(choice.x>=0?choice.unit[0].a:-1)<<",\"b\":"<<(choice.x>=0?choice.unit[0].b:-1)<<",\"ha\":"<<choice.ha<<",\"hb\":"<<choice.hb<<",\"modes\":[";
 for(int mode=0;mode<2;mode++){
  Solver s=*base;auto design=*d;
  if(mode&&choice.x>=0){
   design.unit[choice.x]=choice.unit[0];design.unit[choice.y]=choice.unit[1];if(choice.z>=0)design.unit[choice.z]=choice.unit[2];design.rebuild();
   s.forced_helper[choice.unit[0].a]=choice.ha+7;s.forced_helper[choice.unit[0].b]=choice.hb+7;
   materialize(s,design);
   assert(s.helper_required[choice.unit[0].a]&&s.helper_required[choice.unit[0].b]);
   for(int u:{choice.unit[0].a,choice.unit[0].b}){
    bool found=false;for(auto&h:s.interleave->helpers[u])if(h.paper==s.forced_helper[u])found=true;assert(found);
   }
  }
  auto state=s.save();long long total=0,wrong=0,special_total=0,special_count=0;
  for(int q=0;q<sequences;q++){
   s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
    auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(choice.x>=0&&(u==choice.unit[0].a||u==choice.unit[0].b))special_total+=path.size(),special_count++;
    if(q==0){
     for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 covered=0;for(int j=0;j<at;j++)covered|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~covered);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);assert(!s.plan_failures);double avg=double(total)/(sequences*1024);if(!mode)reference=avg;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"special_moves\":"<<double(special_total)/std::max(1LL,special_count)<<"}"<<std::flush;
 }
 std::cout<<"]}\n";
}
