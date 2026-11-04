#define PATCH_CODE_NO_MAIN
#include "pair_model.hpp"
struct Search:patch_code::Model {
 struct Eval{double value=1e9;int eligible=0,novel=0,special=0,selected=0;std::vector<int> chosen;};
 std::vector<double> prices;std::vector<int> covered;std::vector<std::pair<double,int>> ranked;
 double charge=2;int need=72;XorShift rng{610000007};
 Eval eval(u64 mask,u64 color,int h,int hc,bool force=false){
  prices.assign(pairs.size(),1e6);covered.assign(pairs.size(),-1);ranked.clear();
  for(int i=0;i<int(pairs.size());i++){
   auto&p=pairs[i];double cost=p.old;
   int who=-1;
   if(mask&&(p.diff&mask)){
    for(int t:{p.a,p.b})if(!((A[t]^color)&mask)&&int(A[t]>>h&1)==hc){who=t;break;}
    if(who>=0){auto r=comp.closure(A[p.a],p.diff&~mask);u64 key=0;bool ok=true;for(int x=0;x<6;x++){ok&=!(r[x]>>x&1);key|=u64(r[x])<<(8*x);}if(ok){double v=PosetSums::get().both_of(key)/720.+charge;if(cost<0||v<cost)cost=v;else who=-1;}else who=-1;}
   }
   if(cost<0)continue;prices[i]=p.fixed+cost;covered[i]=who;ranked.emplace_back(prices[i],i);
  }
  std::sort(ranked.begin(),ranked.end());std::array<bool,256>used{};Eval e;e.eligible=ranked.size();double sum=0;
  for(auto[v,i]:ranked){auto&p=pairs[i];if(used[p.a]||used[p.b])continue;used[p.a]=used[p.b]=true;sum+=v;e.chosen.push_back(i);if(int(e.chosen.size())==need)break;}
  if(int(e.chosen.size())<need){
   std::array<std::vector<std::pair<int,int>>,256> neighbours;for(auto[v,i]:ranked){auto&p=pairs[i];neighbours[p.a].emplace_back(p.b,i);neighbours[p.b].emplace_back(p.a,i);}
   while(int(e.chosen.size())<need){double best=1e8;int bx=-1,bi=-1,bj=-1,bu=-1,bv=-1;
    for(int x=0;x<int(e.chosen.size());x++){auto&p=pairs[e.chosen[x]];for(auto[u,i]:neighbours[p.a])if(!used[u])for(auto[v,j]:neighbours[p.b])if(!used[v]&&u!=v){double d=prices[i]+prices[j]-prices[e.chosen[x]];if(d<best)best=d,bx=x,bi=i,bj=j,bu=u,bv=v;}}
    if(bx<0)break;used[bu]=used[bv]=true;sum+=best;e.chosen[bx]=bi;e.chosen.push_back(bj);
   }
  }
  for(int i:e.chosen){e.novel+=pairs[i].old<0;e.special+=covered[i]>=0;}e.selected=e.chosen.size();e.value=sum/256+10*(need-e.selected);return e;
 }
};
#ifndef OVERPATCH_NO_MAIN
int main(int argc,char**argv){if(argc<3)return 2;auto s=std::make_unique<Search>();if(!s->load(argv[1],argv[2]))return 3;
 int iterations=argc>3?std::stoi(argv[3]):30000;s->charge=argc>4?std::stod(argv[4]):2.;int maxbits=argc>5?std::stoi(argv[5]):10;auto start=std::chrono::steady_clock::now();
 s->need=71;auto base=s->eval(0,0,38,0);s->need=72;auto none=s->eval(0,0,38,0);u64 mask=0,color=0,bm=0,bc=0;int h=38,hc=0,bh=h,bhc=hc;auto cur=none,best=none;
 for(int t=0;t<iterations;t++){
  double temp=.02*std::pow(.005,double(t)/iterations);u64 nm=mask,nc=color;int nh=h,nhc=hc;int kind=s->rng.mod(8),j=s->rng.mod(s->G);
  if(kind<3){nm^=1ULL<<j;if(s->rng.mod(2))nc^=1ULL<<j;}
  else if(kind==3){nc^=1ULL<<j;}
  else if(kind==4){nh=s->G+s->rng.mod(63-s->G);nhc=s->rng.mod(2);}
  else if(kind==5){int k=s->rng.mod(s->G);if(((nm>>j)^(nm>>k))&1)nm^=(1ULL<<j)|(1ULL<<k);if(((nc>>j)^(nc>>k))&1)nc^=(1ULL<<j)|(1ULL<<k);}
  else{auto&p=s->pairs[s->rng.mod(s->pairs.size())];if(p.old>=0)continue;nm|=p.residual;nc=(nc&~p.residual)|(s->A[s->rng.mod(2)?p.a:p.b]&p.residual);}
  nc&=nm;if(__builtin_popcountll(nm)>maxbits)continue;auto next=s->eval(nm,nc,nh,nhc);
  if(next.value<cur.value||s->rng.real()<std::exp((cur.value-next.value)/temp))mask=nm,color=nc,h=nh,hc=nhc,cur=std::move(next);
  if(cur.value<best.value){best=cur;bm=mask;bc=color;bh=h;bhc=hc;}
 }
 auto final=s->eval(bm,bc,bh,bhc);std::cout<<std::setprecision(12)<<"{\"base\":"<<base.value<<",\"none\":"<<none.value<<",\"best\":"<<best.value<<",\"difference\":"<<best.value-base.value<<",\"selected\":"<<best.selected<<",\"novel\":"<<best.novel<<",\"special\":"<<best.special<<",\"eligible\":"<<best.eligible<<",\"mask\":"<<bm<<",\"color\":"<<bc<<",\"handle\":"<<bh<<",\"handle_color\":"<<bhc<<",\"charge\":"<<s->charge<<",\"maxbits\":"<<maxbits<<",\"iterations\":"<<iterations<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
#endif
