#include "common.hpp"
constexpr int F=8;
using Features=std::array<double,F>;
Features features(const Solver&s,const std::array<int,K>&frequency){
 Features f{};std::array<int,64>rank{};std::array<std::array<int,2>,64>first;for(auto&v:first)v={-1,-1};
 std::array<std::array<bool,2>,64>available{};std::array<bool,K>extra{};
 if(s.top_d>=0)extra[s.top_d]=true;for(auto x:s.fillers)extra[x.paper]=true;
 for(int k:s.order){int c=s.col_of[k];if(c<0)continue;int b=s.paper[k].black>>s.handle[c]&1;
  if(extra[k]){available[c][b]=true;continue;}
  if(first[c][b]<0)first[c][b]=rank[c];
  f[0]+=frequency[k]*rank[c]/double(P);f[1]+=(s.adaptive_weights[k]-frequency[k])*rank[c]/double(P);rank[c]++;
 }
 std::array<std::array<double,2>,64>covered{};
 for(auto x:s.fillers){
  bool low=s.below_generic(x.paper);f[low?3:4]++;
  if(low){auto&v=s.stay_table[x.paper][x.lvl];f[5]+=.4-v.probability;
   for(int c=0;c<s.H;c++){int b=s.h_blk[x.paper]>>c&1;covered[c][b]=std::max(covered[c][b],v.cover[c]);}
  }
 }
 for(int c=0;c<s.H;c++)for(int b=0;b<2;b++){int fix=available[c][b]?0:first[c][b];if(fix<0)fix=rank[c];f[2]+=s.adaptive_holes[c][b]*fix;f[6]+=covered[c][b]*fix;}
 f[7]=s.fillers.size()*(s.fillers.size()-1)/2.;
 double expected=f[0]+f[1]+f[2]+.6*(f[3]+f[4])+.25*f[5]-.25*f[6];
 assert(std::abs(expected-s.adaptive_next_cost()-s.filler_charge())<1e-7);return f;
}
struct Row{Features f;double cost;};
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto d=recover(*base);
 d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);
 Solver s=*base;materialize(s,*d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();
 s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
 std::array<int,K>frequency{};for(int u=0;u<P;u++)frequency[s.ded[u]]++;
 int sequences=argc>3?std::stoi(argv[3]):16;std::vector<std::vector<Row>>all;auto initial=s.save();Features mean{};double avgcost=0;int samples=0;
 for(int q=0;q<sequences;q++){
  s.restore(initial);std::mt19937_64 rng(91183310000003ULL*(q+1));int prev=rng()%P;std::vector<Row>rows;
  for(int t=0;t<1024;t++){
   auto f=features(s,frequency);int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);assert(s.display()==s.A[u]);
   if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   if(t>=64){rows.push_back({f,double(path.size())});for(int i=0;i<F;i++)mean[i]+=f[i];avgcost+=path.size();samples++;}
  }
  rows.push_back({features(s,frequency),0});all.push_back(std::move(rows));
 }
 assert(!s.plan_failures);for(double&v:mean)v/=samples;avgcost/=samples;
 std::cout<<std::setprecision(16)<<"{\"mean_cost\":"<<avgcost<<",\"samples\":"<<samples<<",\"horizons\":[";int z=0;
 for(int horizon:{1,4,16,64}){
  std::array<std::array<double,F>,F>A{},cov{};Features b{};int n=0;
  for(const auto&rows:all)for(int t=0;t+horizon<int(rows.size());t++){
   double target=0;for(int k=0;k<horizon;k++)target+=rows[t+k].cost-avgcost;
   for(int i=0;i<F;i++){double x=rows[t].f[i]-mean[i];b[i]+=x*target;
    for(int j=0;j<F;j++){A[i][j]+=x*(rows[t].f[j]-rows[t+horizon].f[j]);cov[i][j]+=x*(rows[t].f[j]-mean[j]);}}
   n++;
  }
  std::cout<<(z++?",":"")<<"{\"steps\":"<<horizon<<",\"n\":"<<n<<",\"A\":[";
  for(int i=0;i<F;i++)for(int j=0;j<F;j++)std::cout<<((i||j)?",":"")<<A[i][j];std::cout<<"],\"b\":[";
  for(int i=0;i<F;i++)std::cout<<(i?",":"")<<b[i];std::cout<<"],\"cov\":[";
  for(int i=0;i<F;i++)for(int j=0;j<F;j++)std::cout<<((i||j)?",":"")<<cov[i][j];std::cout<<"]}";
 }
 std::cout<<"]}\n";
}
